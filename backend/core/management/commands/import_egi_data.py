import os
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from core.models import Egi, EgiColor  # 실제 앱 이름(core)이 맞는지 확인하세요!


class Command(BaseCommand):
    help = "CSV 데이터를 읽어 이미지를 S3에 업로드하고 DB에 저장합니다 (이미 있으면 업로드 스킵)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="CSV 파일 경로")
        parser.add_argument(
            "image_dir", type=str, help="이미지 파일들이 들어있는 로컬 폴더 경로"
        )

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs["csv_file"]
        image_dir_path = kwargs["image_dir"]

        # --- 1. AWS S3 설정 (안전하게 가져오기) ---
        aws_region = getattr(settings, "AWS_REGION", "ap-northeast-2")
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=aws_region,
        )

        self.stdout.write(f"Reading CSV file: {csv_file_path}")

        # CSV 파일 읽기
        try:
            df = pd.read_csv(csv_file_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file_path, encoding="cp949")

        df = df.fillna("")
        success_count = 0

        # --- 2. 데이터 순회 ---
        for index, row in df.iterrows():
            try:
                # [중요] 한 줄(Row)마다 트랜잭션을 걸어, 에러가 나도 다른 데이터는 저장되게 함
                with transaction.atomic():
                    img_filename = row.get("이미지", "").strip()
                    brand_name = row.get("브랜드", "").strip()
                    product_name = row.get("이름", "").strip()
                    color_category = row.get("색 카테고리", "").strip()
                    size_val = str(row.get("사이즈 (mm)", "")).strip()
                    link_val = row.get("출처(선택)", "").strip()
                    if not product_name:
                        continue

                    # (A) 색상 처리
                    if color_category:
                        egi_color, _ = EgiColor.objects.get_or_create(
                            color_name=color_category
                        )
                    else:
                        egi_color, _ = EgiColor.objects.get_or_create(
                            color_name="Unknown"
                        )

                    # (B) S3 이미지 처리 (스마트 로직 적용)
                    image_url = ""
                    if img_filename:
                        s3_key = f"egi_images/{img_filename}"
                        file_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"

                        # S3에 파일이 실제로 있는지 확인 (Head Object)
                        try:
                            s3.head_object(Bucket=bucket_name, Key=s3_key)
                            # 에러가 안 나면 파일이 있다는 뜻 -> 업로드 스킵
                            image_url = file_url
                            # self.stdout.write(f"Skipping Upload (Exists): {img_filename}") # 너무 많으면 주석 처리

                        except ClientError:
                            # 파일이 없으면(404) -> 업로드 진행
                            local_img_path = os.path.join(image_dir_path, img_filename)
                            if os.path.exists(local_img_path):
                                self.stdout.write(f"Uploading new file: {img_filename}")
                                s3.upload_file(
                                    local_img_path,
                                    bucket_name,
                                    s3_key,
                                    ExtraArgs={"ContentType": "image/png"},
                                )
                                image_url = file_url
                            else:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"File missing locally & remotely: {img_filename}"
                                    )
                                )

                    # (C) DB 저장
                    Egi.objects.update_or_create(
                        name=product_name,
                        color=egi_color,
                        defaults={
                            "brand": brand_name,
                            "image_url": image_url,
                            "size": size_val,
                            "purchase_url": link_val,
                        },
                    )
                    success_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing row {index}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Finished! Processed {success_count} items.")
        )
