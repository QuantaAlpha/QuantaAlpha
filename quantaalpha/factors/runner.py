import pickle
import sys
from pathlib import Path
from typing import List
import os
import pandas as pd
from pandarallel import pandarallel

from quantaalpha.core.conf import RD_AGENT_SETTINGS
from quantaalpha.core.utils import cache_with_pickle, multiprocessing_wrapper
from quantaalpha.factors.coder.config import FACTOR_COSTEER_SETTINGS

pandarallel.initialize(verbose=1)

from quantaalpha.components.runner import CachedRunner
from quantaalpha.core.exception import FactorEmptyError
from quantaalpha.log import logger
from quantaalpha.factors.experiment import QlibFactorExperiment

DIRNAME = Path(__file__).absolute().resolve().parent
DIRNAME_local = Path.cwd()

# class QlibFactorExpWorkspace:

#     def prepare():
#         # create a folder;
#         # copy template
#         # place data inside the folder `combined_factors`
#         #
#     def execute():
#         de = DockerEnv()
#         de.run(local_path=self.ws_path, entry="qrun conf.yaml")

# TODO: supporting multiprocessing and keep previous results


class QlibFactorRunner(CachedRunner[QlibFactorExperiment]):
    """
    Docker run
    Everything in a folder
    - config.yaml
    - price-volume data dumper
    - `data.py` + Adaptor to Factor implementation
    - results in `mlflow`
    """

    def calculate_information_coefficient(
        self, concat_feature: pd.DataFrame, SOTA_feature_column_size: int, new_feature_columns_size: int
    ) -> pd.DataFrame:
        res = pd.Series(index=range(SOTA_feature_column_size * new_feature_columns_size))
        for col1 in range(SOTA_feature_column_size):
            for col2 in range(SOTA_feature_column_size, SOTA_feature_column_size + new_feature_columns_size):
                res.loc[col1 * new_feature_columns_size + col2 - SOTA_feature_column_size] = concat_feature.iloc[
                    :, col1
                ].corr(concat_feature.iloc[:, col2])
        return res

    def deduplicate_new_factors(self, SOTA_feature: pd.DataFrame, new_feature: pd.DataFrame) -> pd.DataFrame:
        # calculate the IC between each column of SOTA_feature and new_feature
        # if the IC is larger than a threshold, remove the new_feature column
        # return the new_feature

        concat_feature = pd.concat([SOTA_feature, new_feature], axis=1)
        IC_max = (
            concat_feature.groupby("datetime")
            .parallel_apply(
                lambda x: self.calculate_information_coefficient(x, SOTA_feature.shape[1], new_feature.shape[1])
            )
            .mean()
        )
        IC_max.index = pd.MultiIndex.from_product([range(SOTA_feature.shape[1]), range(new_feature.shape[1])])
        IC_max = IC_max.unstack().max(axis=0)
        return new_feature.iloc[:, IC_max[IC_max < 0.99].index]

    @cache_with_pickle(CachedRunner.get_cache_key, CachedRunner.assign_cached_result)
    def develop(self, exp: QlibFactorExperiment, use_local: bool = True) -> QlibFactorExperiment:
        
        """
        Generate the experiment by processing and combining factor data,
        then passing the combined data to Docker or local environment for backtest results.
        """
        
        if exp.based_experiments and exp.based_experiments[-1].result is None:
            exp.based_experiments[-1] = self.develop(exp.based_experiments[-1], use_local=use_local)

        if exp.based_experiments:
            SOTA_factor = None
            if len(exp.based_experiments) > 1:
                try:
                    SOTA_factor = self.process_factor_data(exp.based_experiments)
                except FactorEmptyError:
                    logger.warning("SOTA factors processing failed, continuing with new factors only.")
                    SOTA_factor = None

            # Process the new factors data
            try:
                new_factors = self.process_factor_data(exp)
            except FactorEmptyError as e:
                logger.error(f"Failed to process new factors: {e}")
                # Try manual factor execution
                logger.info("Attempting to manually execute factors...")
                for ws in exp.sub_workspace_list:
                    if not (ws.workspace_path / "result.h5").exists():
                        try:
                            # Ensure symlink exists
                            data_source = Path(FACTOR_COSTEER_SETTINGS.data_folder).absolute()
                            if not data_source.is_absolute():
                                data_source = Path(__file__).parent.parent.parent.parent.parent / FACTOR_COSTEER_SETTINGS.data_folder
                            daily_pv_link = ws.workspace_path / "daily_pv.h5"
                            if not daily_pv_link.exists() and (data_source / "daily_pv.h5").exists():
                                os.symlink(str(data_source / "daily_pv.h5"), str(daily_pv_link))
                            
                            # Execute factor
                            import subprocess
                            env = os.environ.copy()
                            project_root = Path(__file__).parent.parent.parent.parent.parent
                            env['PYTHONPATH'] = str(project_root) + os.pathsep + env.get('PYTHONPATH', '')
                            subprocess.check_output(
                                [sys.executable, str(ws.workspace_path / 'factor.py')],
                                cwd=str(ws.workspace_path),
                                stderr=subprocess.STDOUT,
                                env=env,
                                timeout=1200,
                            )
                        except Exception as exec_e:
                            logger.warning(f"Failed to manually execute factor {ws.workspace_path}: {exec_e}")
                
                # Retry processing factor data
                try:
                    new_factors = self.process_factor_data(exp)
                except FactorEmptyError:
                    raise FactorEmptyError("No valid factor data found to merge after manual execution attempt.")
            
            if new_factors.empty:
                raise FactorEmptyError("No valid factor data found to merge.")

            # Combine the SOTA factor and new factors if SOTA factor exists
            if False: # SOTA_factor is not None and not SOTA_factor.empty:
                new_factors = self.deduplicate_new_factors(SOTA_factor, new_factors)
                if new_factors.empty:
                    raise FactorEmptyError("No valid factor data found to merge.")
                combined_factors = pd.concat([SOTA_factor, new_factors], axis=1).dropna()
            else:
                combined_factors = new_factors
                
            if len(combined_factors.columns) >= 2:
                pd.set_option('display.width', 1000)
                logger.info(f"Factor correlation: \n\n{combined_factors.corr()}\n")

            # Sort and nest the combined factors under 'feature'
            combined_factors = combined_factors.sort_index()
            combined_factors = combined_factors.loc[:, ~combined_factors.columns.duplicated(keep="last")]
            new_columns = pd.MultiIndex.from_product([["feature"], combined_factors.columns])
            combined_factors.columns = new_columns
            
            logger.info(f"Factor values this round: \n\n{combined_factors.tail()}\n\n")

            # Save the combined factors to the workspace (parquet format for qlib compatibility)
            parquet_path = exp.experiment_workspace.workspace_path / "combined_factors_df.parquet"
            combined_factors.to_parquet(parquet_path, engine="pyarrow")
            logger.info(f"Saved combined factors to {parquet_path}")


        # Run backtest (local or Docker). Config name must match factor_template files (e.g. conf_baseline.yaml).
        config_name = "conf_baseline.yaml" if len(exp.based_experiments) == 0 else "conf_combined_factors.yaml"
        logger.info(f"Execute factor backtest (Use {'Local' if use_local else 'Docker container'}): {config_name}")
        
        # Ensure workspace and config are ready (execute() does not call before_execute()).
        exp.experiment_workspace.before_execute()
        
        # execute() returns (result_df, execute_qlib_log) or (None, execute_qlib_log)
        result_tuple = exp.experiment_workspace.execute(
            qlib_config_name=config_name,
            run_env={}
        )
        
        # Unpack tuple; take first element (DataFrame)
        result = result_tuple[0] if isinstance(result_tuple, tuple) else result_tuple
        
        if result is not None:
            logger.info(f"Backtesting results: \n{result.iloc[2:] if hasattr(result, 'iloc') else result}")
        else:
            logger.warning("Backtesting result is None. Check the execution logs above for errors.")
            if isinstance(result_tuple, tuple) and len(result_tuple) > 1:
                logger.info(f"Execution log: {result_tuple[1][:500]}...")
        
        exp.result = result

        return exp

    def process_factor_data(self, exp_or_list: List[QlibFactorExperiment] | QlibFactorExperiment) -> pd.DataFrame:
        """
        Process and combine factor data from experiment implementations.

        Args:
            exp (ASpecificExp): The experiment containing factor data.

        Returns:
            pd.DataFrame: Combined factor data without NaN values.
        """
        if isinstance(exp_or_list, QlibFactorExperiment):
            exp_or_list = [exp_or_list]
        factor_dfs = []

        # Collect all exp's dataframes
        for exp in exp_or_list:
            # Iterate over sub-implementations and execute them to get each factor data
            message_and_df_list = multiprocessing_wrapper(
                [(implementation.execute, ("All",)) for implementation in exp.sub_workspace_list],
                n=RD_AGENT_SETTINGS.multi_proc_n,
            )
            for idx, (message, df) in enumerate(message_and_df_list):
                # Check if factor generation was successful
                if df is not None and "datetime" in df.index.names:
                    # ----------------------------------------------------------
                    # Ensure on-disk result.h5 is up-to-date.
                    # When execute("All") returns from the pickle cache the
                    # subprocess does NOT re-run, so the file on disk may still
                    # contain stale Debug data.  Re-save the authoritative "All"
                    # DataFrame here so that cache_location in the factor
                    # library always points to the correct data.
                    # ----------------------------------------------------------
                    if idx < len(exp.sub_workspace_list):
                        ws = exp.sub_workspace_list[idx]
                        result_h5 = ws.workspace_path / "result.h5"
                        try:
                            df.to_hdf(str(result_h5), key="data")
                        except Exception as e:
                            logger.debug(f"Could not refresh result.h5 for {ws.workspace_path}: {e}")

                    # Convert Series to DataFrame if needed
                    if isinstance(df, pd.Series):
                        # Get factor name from the corresponding workspace (order should match)
                        if idx < len(exp.sub_workspace_list):
                            factor_name = getattr(exp.sub_workspace_list[idx].target_task, 'factor_name', None)
                            if factor_name:
                                df = df.to_frame(name=factor_name)
                            else:
                                df = df.to_frame(name=df.name if df.name else f'factor_{idx}')
                        else:
                            df = df.to_frame(name=df.name if df.name else f'factor_{idx}')
                    time_diff = df.index.get_level_values("datetime").to_series().diff().dropna().unique()
                    if pd.Timedelta(minutes=1) not in time_diff:
                        factor_dfs.append(df)

        # Combine all successful factor data
        if factor_dfs:
            return pd.concat(factor_dfs, axis=1)
        else:
            raise FactorEmptyError("No valid factor data found to merge.")
