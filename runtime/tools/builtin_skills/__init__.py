from runtime.tools.builtin_skills.content_extract import ContentExtractSkill
from runtime.tools.builtin_skills.travel_briefing_formatter import (
    TravelBriefingFormatterSkill,
)

CODE_SKILL_EXECUTORS = {
    ContentExtractSkill.name: ContentExtractSkill,
    TravelBriefingFormatterSkill.name: TravelBriefingFormatterSkill,
}
