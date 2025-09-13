from datetime import datetime
from beanie import Document, before_event, Insert, Update
from typing import Dict, Any, Optional
from pydantic import Field
from enum import Enum

class SetupStatus(str, Enum):
    """セットアップの状態"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class SetupStep(str, Enum):
    """セットアップのステップ"""
    CREATE_SUPER_ADMIN = "create_super_admin"
    SET_SERVER_INFO = "set_server_info"
    SET_SERVER_SETTINGS = "set_server_settings"

class SetupProgress(Document):
    """セットアップの進捗状況を管理するモデル"""
    status: SetupStatus = Field(default=SetupStatus.NOT_STARTED, description="セットアップの全体状態")
    current_step: Optional[SetupStep] = Field(default=None, description="現在のステップ")
    completed_steps: list[SetupStep] = Field(default_factory=list, description="完了したステップのリスト")
    step_details: Dict[str, Any] = Field(default_factory=dict, description="各ステップの詳細情報")
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    @before_event(Insert)
    def before_insert(self):
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    @before_event(Update)
    def before_update(self):
        self.updated_at = datetime.now()
    
    def start_setup(self):
        """セットアップを開始する"""
        self.status = SetupStatus.IN_PROGRESS
        self.current_step = SetupStep.CREATE_SUPER_ADMIN
    
    def complete_step(self, step: SetupStep, details: Optional[Dict[str, Any]] = None):
        """ステップを完了する"""
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        
        if details:
            self.step_details[step.value] = details
        
        # 次のステップを設定
        if step == SetupStep.CREATE_SUPER_ADMIN:
            self.current_step = SetupStep.SET_SERVER_INFO
        elif step == SetupStep.SET_SERVER_INFO:
            self.current_step = SetupStep.SET_SERVER_SETTINGS
        elif step == SetupStep.SET_SERVER_SETTINGS:
            self.current_step = None
            self.status = SetupStatus.COMPLETED
    
    def get_progress_percentage(self) -> int:
        """進捗率を取得する（0-100）"""
        total_steps = len(SetupStep)
        completed_steps = len(self.completed_steps)
        return int((completed_steps / total_steps) * 100)
    
    def get_next_step(self) -> Optional[SetupStep]:
        """次のステップを取得する"""
        if self.status == SetupStatus.COMPLETED:
            return None
        
        if not self.completed_steps:
            return SetupStep.CREATE_SUPER_ADMIN
        
        if SetupStep.CREATE_SUPER_ADMIN not in self.completed_steps:
            return SetupStep.CREATE_SUPER_ADMIN
        elif SetupStep.SET_SERVER_INFO not in self.completed_steps:
            return SetupStep.SET_SERVER_INFO
        elif SetupStep.SET_SERVER_SETTINGS not in self.completed_steps:
            return SetupStep.SET_SERVER_SETTINGS
        
        return None
    
    def is_step_completed(self, step: SetupStep) -> bool:
        """指定されたステップが完了しているかチェックする"""
        return step in self.completed_steps
    
    def to_dict(self) -> Dict[str, Any]:
        """JSONシリアライズ用の辞書を返す"""
        return {
            "id": str(self.id),
            "status": self.status.value,
            "current_step": self.current_step.value if self.current_step else None,
            "completed_steps": [step.value for step in self.completed_steps],
            "progress_percentage": self.get_progress_percentage(),
            "next_step": self.get_next_step().value if self.get_next_step() else None,
            "step_details": self.step_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    async def get_or_create_setup_progress(cls) -> "SetupProgress":
        """セットアップ進捗を取得する（存在しない場合は作成）"""
        progress = await cls.find_one()
        if not progress:
            progress = cls()
            await progress.insert()
        return progress
    
    @classmethod
    async def reset_setup_progress(cls):
        """セットアップ進捗をリセットする"""
        progress = await cls.find_one()
        if progress:
            progress.status = SetupStatus.NOT_STARTED
            progress.current_step = None
            progress.completed_steps = []
            progress.step_details = {}
            await progress.save()
        else:
            progress = cls()
            await progress.insert()
        return progress
