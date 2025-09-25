from django.core.management.base import BaseCommand
from django.db import connection
import json

class Command(BaseCommand):
    help = 'Migrate Eupago V2 settings from old format to new format'

    def handle(self, *args, **options):
        """
        Migrate settings from the old format ({identifier}_enabled) to the new format (_enabled)
        """
        self.stdout.write(self.style.SUCCESS('Starting Eupago V2 settings migration...'))
        
        # List of payment method identifiers
        payment_methods = ['eupago_cc', 'eupago_mbway', 'eupago_multibanco', 'eupago_payshop']
        
        # Direct SQL approach to migrate settings without requiring hierarkey or other dependencies
        try:
            with connection.cursor() as cursor:
                # Get all event settings
                cursor.execute("SELECT * FROM pretix_settings_hierarkeysetting WHERE key LIKE '%eupago_%_enabled'")
                rows = cursor.fetchall()
                
                migrated_count = 0
                for row in rows:
                    # Extract key and value from the row
                    setting_id = row[0]
                    object_type = row[1]
                    object_id = row[2]
                    key = row[3]
                    value = row[4]
                    
                    # Check if this is one of our payment method settings
                    for method in payment_methods:
                        old_key = f"{method}_enabled"
                        if key == old_key:
                            # Create new key (with double underscore)
                            new_key = f"{method}__enabled"
                            
                            # Insert new setting
                            cursor.execute(
                                "INSERT INTO pretix_settings_hierarkeysetting (object_type, object_id, key, value) VALUES (%s, %s, %s, %s)",
                                [object_type, object_id, new_key, value]
                            )
                            
                            # Delete old setting
                            cursor.execute(
                                "DELETE FROM pretix_settings_hierarkeysetting WHERE id = %s",
                                [setting_id]
                            )
                            
                            migrated_count += 1
                            self.stdout.write(f"Migrated {old_key} to {new_key} for {object_type} {object_id}")
                            break
                
                self.stdout.write(self.style.SUCCESS(f'Successfully migrated {migrated_count} settings'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during migration: {str(e)}'))
            return
            
        self.stdout.write(self.style.SUCCESS('Eupago V2 settings migration completed!'))
