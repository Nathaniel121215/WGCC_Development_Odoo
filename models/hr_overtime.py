from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
import json

def convert_time_to_float(time):
    hours = time.seconds // 3600
    minutes = (time.seconds // 60) % 60
    total_hrs = float(minutes) / 60 + hours
    return total_hrs
class TrueMoveHrOvertime(models.Model):
    _inherit = 'hr.overtime'
    
    # add domain and filtering for domain and department
    domain_id = fields.Many2one('hr.domain', string='Domain')
    domain_id_domain = fields.Char(compute="_compute_domain_id_domain", readonly=True, store=False)
    department_id_domain = fields.Char(compute="_compute_department_id_domain", readonly=True, store=False)

    # for json.dumps to work, the module web_domain_field must be installed then update all modules
    @api.multi
    @api.depends('emp_ids')
    def _compute_domain_id_domain(self):
        for record in self:
            if record.emp_ids:
                record.domain_id_domain = json.dumps(
                [('id', '=', record.emp_ids[0].domain_id.id)]
                )
    @api.multi
    @api.depends('emp_ids')
    def _compute_department_id_domain(self):
        for record in self:
            if record.emp_ids:
                record.department_id_domain = json.dumps(
                [('id', '=', record.emp_ids[0].department_id.id)]
                )
    @api.onchange('emp_ids')
    def _onchange_emp_ids_auto_fill_domain_and_department(self):
        for record in self:
            if record.emp_ids:
                record.domain_id = record.emp_ids[0].domain_id.id
                record.dept_id = record.emp_ids[0].department_id.id
    @api.onchange('dept_id')
    def onchange_dept_id(self):
        if self.dept_id:
            res_emp = self.env['hr.employee'].search([('id','=',self.emp_ids[0].id)])
            emp_ids = []
            for rec_emp in res_emp:
                emp_ids.append(rec_emp.id)

            return {'domain': {'employee_ids': [('id', 'in', emp_ids)],
                               'emp_ids': [('id', 'in', emp_ids)],}}
    # add domain and filtering for domain and department - END
 
    @api.multi
    def action_confirm(self):
        for line in self.overtime_det_ids:
            weekdays_list = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']
            holiday = self.env['hr.holidays.public.line'].search([('date', '=', line.start_date)], limit=1)
            day_date = datetime.strptime(line.start_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%a')
            required_start_weekdays =  convert_time_to_float(timedelta(hours=18, minutes=00))

            required_end =  convert_time_to_float(timedelta(hours=8, minutes=30))

            graveyard_ot = False

            start_time = float('%.2f' % line.start_time)
            if float('%.2f' % required_end) > start_time >= 0.0:
                graveyard_ot = True

            if day_date in weekdays_list and not holiday:
                if start_time < float('%.2f' % required_start_weekdays) and not graveyard_ot:
                    raise ValidationError("Weekdays Overtime starts at 18:00 onwards")
        result = super(TrueMoveHrOvertime, self).action_confirm()
        return result