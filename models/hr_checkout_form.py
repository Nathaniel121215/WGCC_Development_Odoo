from odoo import api, models, fields
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz

# Code from thai_support_hour 
def seconds(td):
    assert isinstance(td, timedelta)
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10. ** 6


def convert_datetime_local(self, dt):
    sdtf = DEFAULT_SERVER_DATETIME_FORMAT
    user_tz = self.env.user.tz or str(pytz.utc)
    local = pytz.timezone(user_tz)

    time_hm = datetime.strftime(pytz.utc.localize(datetime.strptime(dt, sdtf)).astimezone(local), "%H:%M")
    dt_time = datetime.strptime(time_hm + ':00', "%H:%M:%S") - datetime.strptime('00:00:00', "%H:%M:%S")
    dt_ttf = seconds(dt_time) / 3600
    dt_date = datetime.strftime(pytz.utc.localize(datetime.strptime(dt, sdtf)).astimezone(local), "%Y-%m-%d")
    local_str = datetime.strftime(pytz.utc.localize(datetime.strptime(dt, sdtf)).astimezone(local), '%Y-%m-%d %H:%M:%S')
    local_dt = datetime.strptime(local_str, '%Y-%m-%d %H:%M:%S')

    return {
        'time_hm': time_hm,
        'time': dt_time,
        'ttf': dt_ttf,
        'date': dt_date,
        'local_str': local_str,
        'local_dt': local_dt,
    }
    
class HrCheckout(models.Model):
    _name = 'hr.checkout.form'
    _description = 'Model for Submission of Form'
    
    # ADD ALL THE FIELDS HERE
    name = fields.Char(string='Name')
    description = fields.Text(string='Description')


    # Submit button here
    @api.multi
    def process_form_submission(self):
        
        current_user_id = self.env.user.id
        print("Current user ID:", current_user_id)
        attendance_id = self.env['hr.attendance'].search([('check_out', '=', False) ,  ('employee_id', '=', current_user_id)])
        attendance_obj = self.env['hr.attendance'].browse(attendance_id.id)
        date_time_now = convert_datetime_local(self, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))[
            'local_dt']
        check_out = date_time_now - timedelta(hours=7)
        check_out_str = check_out + timedelta(hours=8)
    
        attendance_obj.write({'check_out': check_out
                            #   'has_submitted_form': True,
                            #   'check_out_msg': 'you have submitted a form',
                              })

