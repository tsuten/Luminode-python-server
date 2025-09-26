"""
画像処理ユーティリティ

画像のバリデーション、サムネイル生成、メタデータ抽出などの
画像関連のユーティリティ機能を提供します。
"""

import io
from typing import Tuple, Optional, Dict, Any, List
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
import mimetypes

from schema.image_schema import ImageFormat, ImageValidationError, ImageValidationResult


class ImageValidator:
    """画像ファイルのバリデーション"""
    
    # 許可されるMIMEタイプ
    ALLOWED_FORMATS = {
        ImageFormat.JPEG.value,
        ImageFormat.PNG.value,
        ImageFormat.GIF.value,
        ImageFormat.WEBP.value
    }
    
    # デフォルト設定
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DIMENSIONS = (4096, 4096)     # 4K
    MIN_DIMENSIONS = (1, 1)           # 最小サイズ

    def __init__(self, max_file_size: int = None, max_dimensions: Tuple[int, int] = None):
        """
        ImageValidatorを初期化
        
        Args:
            max_file_size: 最大ファイルサイズ（バイト）
            max_dimensions: 最大画像サイズ（幅, 高さ）
        """
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE
        self.max_dimensions = max_dimensions or self.MAX_DIMENSIONS

    async def validate(self, file_data: bytes, filename: str) -> ImageValidationResult:
        """
        画像ファイルをバリデーション
        
        Args:
            file_data: ファイルのバイナリデータ
            filename: ファイル名
            
        Returns:
            ImageValidationResult: バリデーション結果
        """
        errors = []
        warnings = []
        file_info = {}

        try:
            # ファイルサイズチェック
            file_size = len(file_data)
            file_info["file_size"] = file_size
            
            if file_size > self.max_file_size:
                errors.append(ImageValidationError(
                    code="FILE_TOO_LARGE",
                    message=f"ファイルサイズが大きすぎます。最大{self.max_file_size / 1024 / 1024:.1f}MBまで",
                    details={"max_size": self.max_file_size, "actual_size": file_size}
                ))

            if file_size == 0:
                errors.append(ImageValidationError(
                    code="EMPTY_FILE",
                    message="ファイルが空です"
                ))
                return ImageValidationResult(is_valid=False, errors=errors)

            # MIMEタイプ推定
            mime_type, _ = mimetypes.guess_type(filename)
            file_info["mime_type"] = mime_type

            # 画像として読み込み可能かチェック
            try:
                with Image.open(io.BytesIO(file_data)) as img:
                    file_info.update({
                        "format": img.format,
                        "mode": img.mode,
                        "width": img.width,
                        "height": img.height,
                        "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info
                    })

                    # フォーマットチェック
                    detected_mime = f"image/{img.format.lower()}"
                    if img.format.lower() == "jpeg":
                        detected_mime = "image/jpeg"
                    
                    file_info["detected_mime_type"] = detected_mime

                    if detected_mime not in self.ALLOWED_FORMATS:
                        errors.append(ImageValidationError(
                            code="UNSUPPORTED_FORMAT",
                            message=f"サポートされていない画像形式です: {img.format}",
                            details={"format": img.format, "allowed_formats": list(self.ALLOWED_FORMATS)}
                        ))

                    # 画像サイズチェック
                    if img.width > self.max_dimensions[0] or img.height > self.max_dimensions[1]:
                        errors.append(ImageValidationError(
                            code="DIMENSIONS_TOO_LARGE",
                            message=f"画像サイズが大きすぎます。最大{self.max_dimensions[0]}x{self.max_dimensions[1]}ピクセルまで",
                            details={
                                "max_width": self.max_dimensions[0],
                                "max_height": self.max_dimensions[1],
                                "actual_width": img.width,
                                "actual_height": img.height
                            }
                        ))

                    if img.width < self.MIN_DIMENSIONS[0] or img.height < self.MIN_DIMENSIONS[1]:
                        errors.append(ImageValidationError(
                            code="DIMENSIONS_TOO_SMALL",
                            message=f"画像サイズが小さすぎます。最小{self.MIN_DIMENSIONS[0]}x{self.MIN_DIMENSIONS[1]}ピクセル必要",
                            details={
                                "min_width": self.MIN_DIMENSIONS[0],
                                "min_height": self.MIN_DIMENSIONS[1],
                                "actual_width": img.width,
                                "actual_height": img.height
                            }
                        ))

                    # 警告の生成
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        warnings.append("ファイルサイズが大きいため、アップロードに時間がかかる可能性があります")

                    if img.width > 2048 or img.height > 2048:
                        warnings.append("画像サイズが大きいため、表示時にリサイズされる可能性があります")

            except Exception as e:
                errors.append(ImageValidationError(
                    code="INVALID_IMAGE",
                    message=f"有効な画像ファイルではありません: {str(e)}",
                    details={"error": str(e)}
                ))

        except Exception as e:
            errors.append(ImageValidationError(
                code="VALIDATION_ERROR",
                message=f"バリデーション中にエラーが発生しました: {str(e)}",
                details={"error": str(e)}
            ))

        return ImageValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            file_info=file_info
        )


class ThumbnailGenerator:
    """サムネイル生成"""

    @staticmethod
    async def generate_thumbnail(
        image_data: bytes, 
        width: int = 150, 
        height: int = 150, 
        quality: int = 80,
        format: str = "JPEG"
    ) -> bytes:
        """
        サムネイル画像を生成
        
        Args:
            image_data: 元画像のバイナリデータ
            width: サムネイルの幅
            height: サムネイルの高さ
            quality: JPEG品質（1-100）
            format: 出力フォーマット
            
        Returns:
            bytes: サムネイルのバイナリデータ
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # RGBモードに変換（JPEGで透明度を避けるため）
                if img.mode in ("RGBA", "LA"):
                    # 透明部分を白に変換
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # アスペクト比を保持してリサイズ
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # サムネイルを中央に配置する場合
                # thumbnail_img = Image.new("RGB", (width, height), (255, 255, 255))
                # offset = ((width - img.width) // 2, (height - img.height) // 2)
                # thumbnail_img.paste(img, offset)
                # img = thumbnail_img

                # バイナリデータとして出力
                output = io.BytesIO()
                save_kwargs = {"format": format}
                if format.upper() == "JPEG":
                    save_kwargs["quality"] = quality
                    save_kwargs["optimize"] = True

                img.save(output, **save_kwargs)
                return output.getvalue()

        except Exception as e:
            raise ValueError(f"サムネイル生成に失敗しました: {str(e)}")


class ImageMetadataExtractor:
    """画像メタデータの抽出"""

    @staticmethod
    async def extract_metadata(image_data: bytes) -> Dict[str, Any]:
        """
        画像からメタデータを抽出
        
        Args:
            image_data: 画像のバイナリデータ
            
        Returns:
            Dict[str, Any]: 抽出されたメタデータ
        """
        metadata = {}
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # 基本情報
                metadata.update({
                    "format": img.format,
                    "mode": img.mode,
                    "width": img.width,
                    "height": img.height,
                    "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info
                })

                # EXIFデータの抽出
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif_data = {}
                    for tag_id, value in img._getexif().items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_data[tag] = value
                    metadata["exif"] = exif_data

                # その他の情報
                if img.info:
                    metadata["info"] = img.info

        except Exception as e:
            metadata["extraction_error"] = str(e)

        return metadata


# 便利な関数
async def validate_image(file_data: bytes, filename: str) -> ImageValidationResult:
    """画像バリデーションの便利関数"""
    validator = ImageValidator()
    return await validator.validate(file_data, filename)


async def create_thumbnail(image_data: bytes, width: int = 150, height: int = 150) -> bytes:
    """サムネイル生成の便利関数"""
    generator = ThumbnailGenerator()
    return await generator.generate_thumbnail(image_data, width, height)
