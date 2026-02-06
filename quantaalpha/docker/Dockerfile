FROM docker.1panel.live/pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

# For GPU support, please choose the proper tag from https://hub.docker.com/r/pytorch/pytorch/tags

RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list  
RUN apt-get clean && apt-get update && apt-get install -y \  
    curl \  
    vim \  
    git \  
    build-essential \
    && rm -rf /var/lib/apt/lists/* 

RUN git clone https://www.ghproxy.cn/https://github.com/microsoft/qlib.git

WORKDIR /workspace/qlib

RUN git reset c9ed050ef034fe6519c14b59f3d207abcb693282 --hard

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN python -m pip install --upgrade cython
RUN python -m pip install -e .

RUN pip install catboost
RUN pip install xgboost
RUN pip install scipy==1.11.4
RUN pip install joblib==1.4.2
