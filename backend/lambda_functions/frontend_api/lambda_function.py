from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.utilities.typing import LambdaContext
from handlers.nba_handler import router

logger = Logger()
app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="*"))
app.include_router(router)


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
