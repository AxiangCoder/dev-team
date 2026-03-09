
import operator

from langchain_core.messages import AnyMessage
from typing_extensions import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field
from typing import List, Optional

# --- 基础组件 ---
class AC(BaseModel):
    scenario: str = Field(..., description="场景描述")
    given: str = Field(..., description="前提条件/环境状态")
    when: str = Field(..., description="触发动作/输入")
    then: str = Field(..., description="预期系统反馈/状态变更")

# --- 用户故事模型 ---
class UserStory(BaseModel):
    story_id: str = Field(..., description="唯一标识符，如 US-001")
    feature_group: str = Field(..., description="所属的功能模块名称")
    title: str = Field(..., description="故事标题")
    priority: str = Field(..., description="优先级: P0, P1, P2")
    user_description: str = Field("", description="标准的 As a... I want... So that... 描述")
    
    # 由 Node 2 填充
    positive_ac: List[AC] = Field(default_factory=list, description="正向/理想路径的验收标准")
    
    # 由 Node 3 填充
    negative_ac: List[AC] = Field(default_factory=list, description="异常分支/边界情况的验收标准")
    constraints: List[str] = Field(default_factory=list, description="业务规则、性能或UI的硬性约束")
    
    is_refined: bool = Field(False, description="标记该故事是否已完成深度丰满")


# --- Node 1 的专用输出模型 ---

class Node1Output(BaseModel):
    epic: str = Field(..., description="史诗级需求名称")
    business_goal: str = Field(..., description="核心业务目标")
    stories: List[UserStory] = Field(..., description="初步拆解的简略故事清单")


class MessagesState(TypedDict, total=False):
    """State shared across the top-level graph and team wrappers."""

    messages: Annotated[list[AnyMessage], operator.add]
    user_input: str
    pedding_story: list[str]
    is_current_finished: bool

