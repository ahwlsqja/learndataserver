# Execute
```
uvicorn app.main:app --reload
```

## Installation
```
pip install fastapi
pip install "uvicorn[standard]"
```

## docker build
```
docker buildx build --platform linux/amd64 -t dataserver .
docker tag dataserver phoonil/dataserver:latest
docker push phoonil/dataserver:latest
```