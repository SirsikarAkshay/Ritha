from django.db import models
from django.conf import settings


class AgentJob(models.Model):
    AGENT_CHOICES = [
        ('daily_look',       'Daily Look Generator'),
        ('packing_list',     'Packing List Generator'),
        ('outfit_planner',   'Trip Outfit Planner'),
        ('cultural_advisor', 'Cultural Advisor'),
        ('conflict_detector','Conflict Detector'),
    ]

    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('running',    'Running'),
        ('completed',  'Completed'),
        ('failed',     'Failed'),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agent_jobs')
    agent_type  = models.CharField(max_length=30, choices=AGENT_CHOICES)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    input_data  = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict, blank=True)
    error       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.agent_type} [{self.status}]'
