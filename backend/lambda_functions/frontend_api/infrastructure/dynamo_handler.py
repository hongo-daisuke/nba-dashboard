import boto3
from boto3.dynamodb.table import TableResource

_dynamodb = boto3.resource("dynamodb")


def get_table(table_name: str) -> TableResource:
    return _dynamodb.Table(table_name)  # type: ignore[return-value]
