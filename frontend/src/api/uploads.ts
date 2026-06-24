import { apiRequest } from "./client";

const DEFAULT_PART_SIZE = 8 * 1024 * 1024;

type InitiateMultipartResponse = {
  bucket: string;
  object_key: string;
  upload_id: string;
  part_size: number;
  parts: Array<{
    part_number: number;
    upload_url: string;
  }>;
};

export async function uploadFileMultipart(params: {
  virtualUserId: string;
  submissionId: string;
  blockId: string;
  file: File;
}): Promise<{ objectKey: string; uploadId: string }> {
  const initiate = await apiRequest<InitiateMultipartResponse>(
    "/uploads/multipart/initiate",
    {
      method: "POST",
      body: JSON.stringify({
        virtual_user_id: params.virtualUserId,
        submission_id: params.submissionId,
        block_id: params.blockId,
        filename: params.file.name,
        content_type: params.file.type || "application/octet-stream",
        file_size: params.file.size,
      }),
    },
  );

  const partSize = initiate.part_size || DEFAULT_PART_SIZE;
  const uploadedParts = [];

  for (const part of initiate.parts) {
    const start = (part.part_number - 1) * partSize;
    const end = Math.min(start + partSize, params.file.size);
    const chunk = params.file.slice(start, end);
    const uploadResponse = await fetch(part.upload_url, {
      method: "PUT",
      body: chunk,
    });

    if (!uploadResponse.ok) {
      throw new Error(`Part upload failed: ${part.part_number}`);
    }

    uploadedParts.push({
      part_number: part.part_number,
      etag: uploadResponse.headers.get("etag") ?? "",
    });
  }

  await apiRequest("/uploads/multipart/complete", {
    method: "POST",
    body: JSON.stringify({
      bucket: initiate.bucket,
      object_key: initiate.object_key,
      upload_id: initiate.upload_id,
      parts: uploadedParts,
    }),
  });

  return {
    objectKey: initiate.object_key,
    uploadId: initiate.upload_id,
  };
}
