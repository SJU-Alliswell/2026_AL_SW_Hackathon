from __future__ import annotations

import json
from math import ceil
from pathlib import Path, PurePath
from typing import Any

import boto3
from botocore.client import Config

from app.core.config import settings


class MinioService:
    def __init__(self) -> None:
        scheme = "https" if settings.minio_secure else "http"
        endpoint_url = f"{scheme}://{settings.minio_endpoint}"
        public_endpoint = settings.minio_public_endpoint or settings.minio_endpoint
        public_endpoint_url = f"{scheme}://{public_endpoint}"
        self.bucket = settings.minio_bucket
        self.client = self._build_client(endpoint_url)
        self.public_client = self._build_client(public_endpoint_url)

    def _build_client(self, endpoint_url: str):
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def build_raw_object_key(
        self,
        virtual_user_id: str,
        submission_id: str,
        block_id: str,
        filename: str,
    ) -> str:
        safe_filename = PurePath(filename).name
        return (
            f"{virtual_user_id}/submissions/{submission_id}/blocks/"
            f"{block_id}/raw/{safe_filename}"
        )

    def build_resume_object_key(self, virtual_user_id: str, submission_id: str) -> str:
        return f"{virtual_user_id}/submissions/{submission_id}/inputs/resume.txt"

    def build_question_object_key(
        self, virtual_user_id: str, submission_id: str, block_id: str
    ) -> str:
        return (
            f"{virtual_user_id}/submissions/{submission_id}/blocks/"
            f"{block_id}/inputs/question.txt"
        )

    def build_analysis_object_key(
        self,
        virtual_user_id: str,
        submission_id: str,
        block_id: str,
        filename: str,
    ) -> str:
        safe_filename = PurePath(filename).name
        return (
            f"{virtual_user_id}/submissions/{submission_id}/blocks/"
            f"{block_id}/analysis/{safe_filename}"
        )

    def initiate_multipart_upload(
        self,
        object_key: str,
        file_size: int,
        content_type: str | None,
        part_size: int = 8 * 1024 * 1024,
    ) -> dict:
        kwargs = {
            "Bucket": self.bucket,
            "Key": object_key,
        }
        if content_type:
            kwargs["ContentType"] = content_type

        response = self.client.create_multipart_upload(**kwargs)
        upload_id = response["UploadId"]
        part_count = max(1, ceil(file_size / part_size))
        parts = [
            {
                "part_number": part_number,
                "upload_url": self.public_client.generate_presigned_url(
                    "upload_part",
                    Params={
                        "Bucket": self.bucket,
                        "Key": object_key,
                        "UploadId": upload_id,
                        "PartNumber": part_number,
                    },
                    ExpiresIn=3600,
                ),
            }
            for part_number in range(1, part_count + 1)
        ]

        return {
            "bucket": self.bucket,
            "object_key": object_key,
            "upload_id": upload_id,
            "part_size": part_size,
            "parts": parts,
        }

    def complete_multipart_upload(
        self,
        bucket: str,
        object_key: str,
        upload_id: str,
        parts: list[dict],
    ) -> None:
        completed_parts = [
            {"PartNumber": part["part_number"], "ETag": part["etag"]}
            for part in sorted(parts, key=lambda item: item["part_number"])
        ]
        self.client.complete_multipart_upload(
            Bucket=bucket,
            Key=object_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": completed_parts},
        )

    def download_object(self, bucket: str, object_key: str, destination: Path) -> None:
        self.client.download_file(bucket, object_key, str(destination))

    def delete_object(self, bucket: str, object_key: str) -> None:
        self.client.delete_object(Bucket=bucket, Key=object_key)

    def put_text(self, object_key: str, text: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=text.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )

    def put_json(self, object_key: str, payload: dict[str, Any]) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )


minio_service = MinioService()
