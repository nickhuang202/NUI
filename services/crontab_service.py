import os
import logging
from crontab import CronTab

logger = logging.getLogger(__name__)

# The command to execute when the cron triggers
CRON_COMMAND_TEMPLATE = "/home/NUI/.venv/bin/python3 /home/NUI/run_scheduled_profile.py '{profile_name}'"
# A distinct comment tag so we know which cron jobs belong to NUI
NUI_CRON_MARKER = "NUI_SCHEDULED_PROFILE:"

class CrontabService:
    """Manages system crontab entries for scheduled test profiles."""
    
    def __init__(self):
        # We edit the current user's crontab
        try:
            self.cron = CronTab(user=True)
        except Exception as e:
            logger.error(f"Failed to initialize CronTab: {e}")
            self.cron = None

    def _get_comment(self, profile_name):
        return f"{NUI_CRON_MARKER}{profile_name}"

    def sync_profile(self, profile_name, cron_rule):
        """
        Add or update a cron job for a specific profile.
        cron_rule is a dict containing 'type' (e.g., 'weekly', 'custom') 
        and the details needed to build the cron expression.
        """
        if not self.cron:
            logger.error("CronTab not initialized, cannot sync profile.")
            return False

        try:
            # 1. Remove any existing job for this profile
            self.remove_profile(profile_name)
            
            # If type is 'single', we don't schedule via cron (it will run once immediately or via a one-off mechanism)
            rule_type = cron_rule.get('type')
            if not rule_type or rule_type == 'single':
                logger.info(f"[CRONTAB] Profile '{profile_name}' is single-run or unbounded. Removed from cron.")
                return True

            # 2. Build the exact cron expression string
            expression = self._build_expression(cron_rule)
            if not expression:
                logger.error(f"Could not build cron expression for rule: {cron_rule}")
                return False

            # 3. Create the new job
            command = CRON_COMMAND_TEMPLATE.format(profile_name=profile_name)
            comment = self._get_comment(profile_name)
            
            job = self.cron.new(command=command, comment=comment)
            job.setall(expression)
            
            # 4. Save to actual system crontab
            self.cron.write()
            
            logger.info(f"[CRONTAB] Synced profile '{profile_name}' with expression: {expression}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing profile '{profile_name}' to crontab: {e}")
            return False

    def remove_profile(self, profile_name):
        """Remove a profile's job from the crontab if it exists."""
        if not self.cron:
            return False
            
        try:
            comment = self._get_comment(profile_name)
            self.cron.remove_all(comment=comment)
            self.cron.write()
            logger.info(f"[CRONTAB] Removed profile '{profile_name}' from cron.")
            return True
        except Exception as e:
            logger.error(f"Error removing profile '{profile_name}' from crontab: {e}")
            return False

    def _build_expression(self, cron_rule):
        """
        Convert the frontend cron_rule dict into a standard cron expression string (* * * * *).
        Note: The MVP frontend doesn't pass the exact time, but because the daily profile 
        starts at 00:00 logically (with tests offset), we schedule the entire profile 
        at midnight (0 0) on the selected days, OR we rely on a custom expression.
        """
        rule_type = cron_rule.get('type')
        
        if rule_type == 'custom':
            # E.g. "0 9 * * 1-5"
            # Extract from the preview string or a direct 'expression' field we should add
            preview = cron_rule.get('preview', '')
            if preview.startswith('Cron: '):
                return preview.replace('Cron: ', '').strip()
            return "* * * * *" # Fallback
            
        elif rule_type == 'daily':
            # Run at midnight every day
            return "0 0 * * *"
            
        elif rule_type == 'weekly':
            # E.g. Every: Mon, Wed -> 0 0 * * 1,3
            # We map strings to cron DOW integers (0=Sun, 1=Mon, ..., 6=Sat)
            preview = cron_rule.get('preview', '')
            if not preview.startswith('Every:'):
                return "0 0 * * 0" # Fallback Sunday
                
            days_str = preview.replace('Every:', '').strip()
            days_list = [d.strip() for d in days_str.split(',')]
            
            day_map = {
                'Sun': '0', 'Mon': '1', 'Tue': '2', 'Wed': '3', 
                'Thu': '4', 'Fri': '5', 'Sat': '6'
            }
            
            cron_days = []
            for d in days_list:
                if d in day_map:
                    cron_days.append(day_map[d])
                    
            if not cron_days:
                return "0 0 * * 0"
                
            days_expr = ",".join(cron_days)
            return f"0 0 * * {days_expr}"
            
        elif rule_type == 'monthly':
            # Run 1st of every month at midnight
            return "0 0 1 * *"
            
        return None
