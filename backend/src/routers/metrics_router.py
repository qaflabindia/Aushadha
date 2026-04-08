import asyncio
import gc
import json
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form

from src.api_response import create_api_response
from src.entities.user_credential import Neo4jCredentials, get_neo4j_credentials
from src.logger import CustomLogger
from src.ragas_eval import get_additional_metrics, get_ragas_metrics
from src.shared.common_fn import formatted_time, get_remaining_token_limits

logger = CustomLogger()
router = APIRouter(tags=["Metrics & Evaluation"])


@router.post('/metric')
async def calculate_metric(
    question: str = Form(),
    context: str = Form(),
    answer: str = Form(),
    model: str = Form(),
    mode: str = Form()
):
    """Calculate RAGAS metrics for a given question, context, and answer."""
    try:
        start = time.time()
        context_list = [str(item).strip() for item in json.loads(context)] if context else []
        answer_list = [str(item).strip() for item in json.loads(answer)] if answer else []
        mode_list = [str(item).strip() for item in json.loads(mode)] if mode else []

        result = await asyncio.to_thread(
            get_ragas_metrics, question, context_list, answer_list, model
        )
        if result is None or "error" in result:
            return create_api_response(
                'Failed',
                message='Failed to calculate evaluation metrics.',
                error=result.get("error", "Ragas evaluation returned null")
            )
        data = {mode: {metric: result[metric][i] for metric in result} for i, mode in enumerate(mode_list)}
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'metric', 'question':question, 'context':context, 'answer':answer, 'model':model,'mode':mode,
                            'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}'}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success', data=data)
    except Exception as e:
        logging.exception(f"Error while calculating evaluation metrics: {e}")
        return create_api_response(
            'Failed',
            message="Error while calculating evaluation metrics",
            error=str(e)
        )
    finally:
        gc.collect()


@router.post('/additional_metrics')
async def calculate_additional_metrics(question: str = Form(),
                                        context: str = Form(),
                                        answer: str = Form(),
                                        reference: str = Form(),
                                        model: str = Form(),
                                        mode: str = Form(),
):
   try:
       context_list = [str(item).strip() for item in json.loads(context)] if context else []
       answer_list = [str(item).strip() for item in json.loads(answer)] if answer else []
       mode_list = [str(item).strip() for item in json.loads(mode)] if mode else []
       result = await get_additional_metrics(question, context_list,answer_list, reference, model)
       if result is None or "error" in result:
           return create_api_response(
               'Failed',
               message='Failed to calculate evaluation metrics.',
               error=result.get("error", "Ragas evaluation returned null")
           )
       data = {mode: {metric: result[i][metric] for metric in result[i]} for i, mode in enumerate(mode_list)}
       return create_api_response('Success', data=data)
   except Exception as e:
       logging.exception(f"Error while calculating evaluation metrics: {e}")
       return create_api_response(
           'Failed',
           message="Error while calculating evaluation metrics",
           error=str(e)
       )
   finally:
       gc.collect()


@router.post("/get_token_limits")
async def get_token_limits(credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    """
    Returns the remaining daily and monthly token limits for a user, given email and/or uri.
    Only enabled if TRACK_TOKEN_USAGE env variable is set to 'true'.
    """
    job_status = "Success"
    message = "Token limits fetched successfully"
    try:
        if os.environ.get("TRACK_TOKEN_USAGE", "false").strip().lower() != "true":
            message = "Token tracking is not enabled."
            return create_api_response(job_status, data=None, message=message)
        start = time.time()
        limits = get_remaining_token_limits(credentials.email, credentials.uri)
        end = time.time()
        elapsed_time = end - start
        json_obj = {
            'api_name': 'get_token_limits',
            'db_url': credentials.uri,
            'email': credentials.email,
            'logging_time': formatted_time(datetime.now(timezone.utc)),
            'elapsed_api_time': f'{elapsed_time:.2f}'
        }
        logger.log_struct(json_obj, "INFO")
        return create_api_response(job_status, data=limits, message=message)
    except Exception as e:
        job_status = "Failed"
        error_message = str(e)
        message = "Unable to fetch token limits"
        logger.log_struct({'api_name': 'get_token_limits', 'db_url': credentials.uri, 'email': credentials.email, 'error_message': error_message, 'logging_time': formatted_time(datetime.now(timezone.utc))}, "ERROR")
        logging.exception(f'Exception in get_token_limits: {error_message}')
        return create_api_response(job_status, message=message, error=error_message)
