# -*- coding: utf-8 -*-
"""Submit a HunYuan 3D generation task."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hy3d_api


def parse_args():
    parser = argparse.ArgumentParser(description="Submit a HunYuan 3D generation task")
    parser.add_argument("--prompt", type=str, default=None, help="Text description for 3D generation")
    parser.add_argument("--image-url", type=str, default=None, help="Input image URL for image-to-3D")
    parser.add_argument("--image-base64", type=str, default=None, help="Input image Base64 for image-to-3D")
    parser.add_argument("--multi-view", type=str, default=None, help="Multi-view images JSON")
    parser.add_argument("--model", type=str, default=None, choices=hy3d_api.VALID_MODELS,
                        help="Model: 3.0, 3.1, hy-3d-3.0, or hy-3d-3.1")
    parser.add_argument("--enable-pbr", action="store_true", default=False, help="Enable PBR material generation")
    parser.add_argument("--face-count", type=int, default=None, help="Face count")
    parser.add_argument("--generate-type", type=str, default=None, choices=hy3d_api.VALID_GENERATE_TYPES,
                        help="Generation type")
    parser.add_argument("--polygon-type", type=str, default=None, choices=hy3d_api.VALID_POLYGON_TYPES,
                        help="Polygon type for LowPoly")
    parser.add_argument("--result-format", type=str, default=None, choices=hy3d_api.VALID_RESULT_FORMATS,
                        help="Output format")
    parser.add_argument("--provider", choices=("auto", "tokenhub", "tencent"), default="auto",
                        help="Backend provider. auto prefers TokenHub when HY3D_OPENAI_API_KEY is configured.")
    parser.add_argument("--region", default="ap-guangzhou", help="Tencent Cloud region for --provider tencent")
    parser.add_argument("--stdin", action="store_true", help="Read JSON parameters from stdin")
    args = parser.parse_args()

    if args.stdin:
        data = json.loads(sys.stdin.read().strip())
        for key, value in data.items():
            attr = key.replace("-", "_")
            if hasattr(args, attr):
                setattr(args, attr, value)
        if isinstance(args.multi_view, list):
            args.multi_view = json.dumps(args.multi_view, ensure_ascii=False)

    ok, message = hy3d_api.validate_inputs(args)
    if not ok:
        print(json.dumps({"error": "INVALID_INPUT", "message": message}, ensure_ascii=False, indent=2))
        sys.exit(1)
    return args


def main():
    hy3d_api.load_local_env()
    args = parse_args()
    try:
        response = hy3d_api.submit(args)
    except Exception as err:
        hy3d_api.print_error(err, "AI3D_API_ERROR")

    if not response.get("job_id"):
        print(json.dumps({
            "error": "NO_JOB_ID",
            "provider": response.get("provider", ""),
            "response": response.get("raw", response),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps({
        "provider": response["provider"],
        "job_id": response["job_id"],
        "request_id": response.get("request_id", ""),
        "model": response.get("model", ""),
        "status": response.get("raw_status", ""),
        "message": "Task submitted successfully. Use query_job.py with the same provider/model to poll for results.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
