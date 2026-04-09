from django.contrib import admin
from .models import AgentJob


@admin.register(AgentJob)
class AgentJobAdmin(admin.ModelAdmin):
    list_display  = ['user', 'agent_type', 'status', 'created_at', 'completed_at']
    list_filter   = ['agent_type', 'status']
    search_fields = ['user__email']
    readonly_fields = ['input_data', 'output_data', 'error', 'created_at', 'completed_at']
