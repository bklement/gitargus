from fastapi import FastAPI, HTTPException
import boto3

app = FastAPI()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('git')

@app.get("/{hostname}")
async def get(hostname : str):
    print(hostname)
    response = table.get_item(Key={"hostname": hostname})
    length = int(response["ResponseMetadata"]["HTTPHeaders"]["content-length"])
    if (length < 10):
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        return response["Item"]
    