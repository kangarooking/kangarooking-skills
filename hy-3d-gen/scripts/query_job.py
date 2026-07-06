# -*- coding: utf-8 -*-
"""Query or poll a HunYuan 3D generation task."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hy3d_api


def parse_args():
    parser = argparse.ArgumentParser(description="Query or poll a HunYuan 3D task")
    parser.add_argument("job_id", help="Job ID returned by submit_job.py or main.py --no-poll")
    parser.add_argument("--model", type=str, default=None, choices=hy3d_api.VALID_MODELS,
                        help="Model used for TokenHub query. Defaults to hy-3d-3.0.")
    parser.add_argument("--provider", choices=("auto", "tokenhub", "tencent"), default="auto",
                        help="Backend provider. auto prefers TokenHub when HY3D_OPENAI_API_KEY is configured.")
    parser.add_argument("--region", default="ap-guangzhou", help="Tencent Cloud region for --provider tencent")
    parser.add_argument("--poll-interval", type=int, default=10, help="Polling interval in seconds")
    parser.add_argument("--max-poll-time", type=int, default=600, help="Max polling time in seconds")
    parser.add_argument("--no-poll", action="store_true", help="Query once without polling")
    args = parser.parse_args()

    ok, message = hy3d_api.validate_inputs(args, for_query=True)
    if not ok:
        print(json.dumps({"error": "INVALID_INPUT", "message": message}, ensure_ascii=False, indent=2))
        sys.exit(1)
    return args


def output_query_result(response):
    result = {
        "provider": response.get("provider", ""),
        "job_id": response.get("job_id", ""),
        "status": response.get("status", ""),
    }
    if response.get("request_id"):
        result["request_id"] = response["request_id"]
    if response.get("error_code"):
        result["error_code"] = response["error_code"]
        result["error_message"] = response.get("error_message", "")
    if response.get("result_files"):
        result["result_files"] = response["result_files"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    hy3d_api.load_local_env()
    args = parse_args()
    try:
        if args.no_poll:
            response = hy3d_api.query(args.job_id, args.provider, args.model, args.region)
        else:
            response = hy3d_api.poll(
                args.job_id,
                args.provider,
                args.model,
                args.region,
                args.poll_interval,
                args.max_poll_time,
            )
        output_query_result(response)
    except Exception as err:
        hy3d_api.print_error(err, "AI3D_API_ERROR")


if __name__ == "__main__":
    main()
