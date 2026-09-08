from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


RiskLevel = Literal["high", "medium", "low"]
TaskStatus = Literal["pending", "processing", "done", "error"]


class AuditRequest(BaseModel):
    brandName: str = Field(min_length=1, max_length=50)
    englishName: str = Field(default="", max_length=100)
    niceClass: str = Field(min_length=1, max_length=100)
    goodsServices: str = Field(default="", max_length=500)
    businessDescription: str = Field(default="", max_length=500)
    targetCountries: list[str] = Field(default_factory=lambda: ["越南"], max_length=10)
    operationStage: Literal["pre-entry", "launching", "operating"] = "pre-entry"
    plannedMarkets: int = Field(default=1, ge=1, le=10)
    hasChinaBaseMark: bool = False
    logo: str = Field(min_length=16, max_length=8_000_000)

    @model_validator(mode="after")
    def normalize_service_description(self) -> "AuditRequest":
        if not self.goodsServices and not self.businessDescription:
            raise ValueError("goodsServices 或 businessDescription 至少填写一项")
        if not self.goodsServices:
            self.goodsServices = self.businessDescription
        if not self.businessDescription:
            self.businessDescription = self.goodsServices
        return self


class TaskCreated(BaseModel):
    taskId: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    company: str = Field(default="", max_length=80)
    inviteCode: str = Field(default="", max_length=32)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)


class UnifiedResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: object | None = None
