# -*- coding: utf-8 -*-
"""Submit and optionally poll a HunYuan 3D generation task."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hy3d_api


def parse_args():
    parser = argparse.ArgumentParser(description="HunYuan 3D generation (submit + optional poll)")
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
    parser.add_argument("--poll-interval", type=int, default=10, help="Polling interval in seconds")
    parser.add_argument("--max-poll-time", type=int, default=600, help="Max polling time in seconds")
    parser.add_argument("--no-poll", action="store_true", help="Submit only and return the job ID")
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


def output_final(response, model=None):
    result = {
        "provider": response.get("provider", ""),
        "job_id": response.get("job_id", ""),
        "status": "success",
        "result_files": response.get("result_files", []),
    }
    if model:
        result["model"] = model
    if response.get("request_id"):
        result["request_id"] = response["request_id"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    hy3d_api.load_local_env()
    args = parse_args()
    try:
        input_desc = args.prompt or args.image_url or "(image-base64)"
        print(f"[INFO] Submitting 3D task: {input_desc[:80]}...", file=sys.stderr)
        submitted = hy3d_api.submit(args)
    except Exception as err:
        hy3d_api.print_error(err, "AI3D_API_ERROR")

    job_id = submitted.get("job_id", "")
    if not job_id:
        print(json.dumps({
            "error": "NO_JOB_ID",
            "provider": submitted.get("provider", ""),
            "response": submitted.get("raw", submitted),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    provider = submitted.get("provider", "")
    model = submitted.get("model", "")
    print(f"[INFO] Submitted provider={provider} job_id={job_id}", file=sys.stderr)

    if args.no_poll:
        print(json.dumps({
            "provider": provider,
            "job_id": job_id,
            "request_id": submitted.get("request_id", ""),
            "model": model,
            "status": submitted.get("raw_status", ""),
            "message": "Task submitted. Use query_job.py to poll for results.",
        }, ensure_ascii=False, indent=2))
        return

    try:
        response = hy3d_api.poll(
            job_id,
            provider,
            model,
            args.region,
            args.poll_interval,
            args.max_poll_time,
        )
    except Exception as err:
        hy3d_api.print_error(err, "AI3D_API_ERROR")

    output_final(response, model=model)
    print("[INFO] Note: generated file URLs are temporary. Save them promptly.", file=sys.stderr)


if __name__ == "__main__":
    main()
