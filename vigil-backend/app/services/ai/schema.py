from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class AIAnalysisFindingSchema(BaseModel):
    title: str
    description: str
    severity: str
    confidence: Optional[float] = None
    category: str
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    evidence: List[str] = Field(default_factory=list)
    reasoning: str
    introduced_by_commit: bool

class AIAnalysisResultSchema(BaseModel):
    summary: str
    overall_assessment: str
    findings: List[AIAnalysisFindingSchema] = Field(default_factory=list)
