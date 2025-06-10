from pydantic import BaseModel, Field

class Structure(BaseModel):
    """
    定义AI需要生成的完整数据结构。
    所有字段均为必需项，以确保AI始终提供完整的分析。
    """
    title_translation: str = Field(
        ..., 
        description="Translate the paper's title into {language}."
    )
    tldr: str = Field(
        ..., 
        description="generate a too long; didn't read summary"
    )
    motivation: str = Field(
        ..., 
        description="describe the motivation in this paper"
    )
    method: str = Field(
        ..., 
        description="method of this paper"
    )
    result: str = Field(
        ..., 
        description="result of this paper"
    )
    conclusion: str = Field(
        ..., 
        description="conclusion of this paper"
    )
    translation: str = Field(
        ..., 
        description="translate the paper to Chinese"
    )
    summary: str = Field(
        ..., 
        description="generate a new, concise summary of the paper based on its abstract"
    )
    keywords: str = Field(
        ..., 
        description="Extract 3 to 5 keywords from the abstract, separated by commas."
    )
    comments: str = Field(
        ..., 
        description="add some insightful comments about this paper, focusing on its innovation, importance, or limitations"
    )

