    
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from datetime import datetime, timedelta
import calendar
import json

class TrueMoveHRHolidays(models.Model):
    _inherit = 'hr.holidays'

    # add domain and filtering for domain and department
    domain_id = fields.Many2one('hr.domain', string='Domain')
    domain_id_domain = fields.Char(compute="_compute_domain_id_domain", readonly=True, store=False)
    department_id_domain = fields.Char(compute="_compute_department_id_domain", readonly=True, store=False)

    # add waiting for cancellation status
    state = fields.Selection(selection_add=[('waiting_to_cancel', 'Waiting for Cancellation')])
    @api.multi
    def action_refuse_cancel(self):
        self.req_cancel = False
        self.state = 'validate'
        return
    @api.multi
    def action_cancel(self):
        self.state = 'cancel'
    # for json.dumps to work, the module web_domain_field must be installed then update all modules
    @api.multi
    @api.depends('employee_id')
    def _compute_domain_id_domain(self):
        for record in self:
            if record.employee_id:
                record.domain_id_domain = json.dumps(
                [('id', '=', record.employee_id.domain_id.id)]
                )
    @api.multi
    @api.depends('employee_id')
    def _compute_department_id_domain(self):
        for record in self:
            if record.employee_id:
                record.department_id_domain = json.dumps(
                [('id', '=', record.employee_id.department_id.id)]
                )
    @api.onchange('employee_id')
    def _onchange_emp_ids_auto_fill_domain_and_department(self):
        for record in self:
            if record.employee_id:
                record.domain_id = record.employee_id.domain_id.id
                record.dept_id = record.employee_id.department_id.id
    # add domain and filtering for domain and department - END

    req_type = fields.Selection([('half_am', 'Half Day - AM'), ('half_pm', 'Half Day - PM'),
                                 ('hours', 'Hour/s'), ('days', 'Day/s')], string='Request Type')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string="End Date",compute='_compute_duration', store=True)
    
    @api.multi
    def name_get(self):
        res = []
        lbl = ''
        for leave in self:
            if leave.req_type == 'hours':
                lbl = "hour(s)"
            elif leave.req_type == 'half_am':
                lbl = "hours (Half Day - AM)"
            elif leave.req_type == 'half_pm':
                lbl = "hours (Half Day - PM)"
            else:
                lbl = "day(s)"

            res.append((leave.id, _("%s on %s : %.2f "+ lbl) % (
                leave.employee_id.name or leave.category_id.name, leave.holiday_status_id.name,
                leave.number_of_days_temp)))


        return res
    
    @api.onchange('req_type')
    def _onchange_req_type(self):
        if self.req_type == 'half_am':
            self.number_of_days_temp = 3.00
        elif self.req_type == 'half_pm':
            self.number_of_days_temp = 5.00
        elif self.req_type == 'hours' or self.req_type == 'days':
            self.number_of_days_temp = 1.00
        else:
            self.number_of_days_temp = 0
    
    @api.onchange('date_to')
    def _onchange_date_to(self):
        pass
    
    @api.onchange('date_from')
    def _onchange_date_from_set_duration(self):
        for record in self:
            if record.date_from:
                if record.req_type == 'half_am':
                    record.number_of_days_temp = 3
                elif record.req_type == 'half_pm':
                    record.number_of_days_temp = 5
                else:
                    record.number_of_days_temp = 1

    @api.multi
    @api.depends('number_of_days_temp')
    def _compute_duration(self):
        for record in self:
            date_from = record.date_from
            date_to = record.date_to
            if record.number_of_days_temp == 0.50:
                record.date_to = record.date_from

            if record.req_type == 'half_am' and record.number_of_days_temp != 3.0:
                raise ValidationError("Half Day - AM leave should be 3 hours.")
            if record.req_type == 'half_pm' and record.number_of_days_temp != 5.0:
                raise ValidationError("Half Day - PM leave should be 5 hours.")

            if record.req_type == 'hours' and record.number_of_days_temp < 0.5:
                raise ValidationError("Hourly leave should not be less than 0.5 hours.")
            elif record.req_type == 'hours' and record.number_of_days_temp > 7:
                raise ValidationError("Hourly leave should not be greater than 7 hours.")
            if record.number_of_days_temp % 1 != 0.0 and record.req_type == 'days':
                raise ValidationError("Duration should be a whole number.")

            if record.req_type in ['half_am','half_pm']:
                record.date_to = record.date_from
            elif record.number_of_days_temp >= 1 and record.req_type not in ['half_am','half_pm','hours']:
                no_of_days_temp = round(record.number_of_days_temp)
                if record.number_of_days_temp > no_of_days_temp:
                    no_of_days_temp += 1
                start_date = datetime.strptime(record.date_from, '%Y-%m-%d')
                end_date = datetime.strptime(date_from, '%Y-%m-%d') + (timedelta(days=(no_of_days_temp - 1.0)))
                # end_date = date_to + timedelta(hours=8)

                days = []
                sat = 0
                sun = 0
                rec = 0

                old_date_to = end_date

                days_wkends = self._get_days(start_date, end_date)
                _days = days_wkends[0]
                _wkends = days_wkends[1]
                record.date_to = end_date
                if 5 in _days and 6 not in _days:
                    record.date_to = end_date + timedelta(days=2)
                elif 5 in _days and 6 in _days:
                    temp_end_date = end_date + timedelta(days=_wkends)
                    if temp_end_date.weekday() == 5 or temp_end_date.weekday() == 6:
                        record.date_to = temp_end_date + timedelta(days=2)
                    else:
                        _wkends_ = self._get_days(start_date, temp_end_date)[1]
                        record.date_to = end_date + timedelta(days=_wkends_)
            else:
                record.date_to = record.date_from
    def _get_days(self, start_date, end_date):
        days = []
        days.append(start_date.weekday())
        while start_date < end_date:
            start_date = start_date + timedelta(days=1)
            days.append(start_date.weekday())
        # print 'dayss', days, old_date_to.weekday()

        sat = days.count(calendar.SATURDAY)
        sun = days.count(calendar.SUNDAY)
        wkends = sat + sun
        return days, wkends

# add waiting for cancellation status
class TrueMoveHolidaysCancellation(models.Model):
    _inherit = 'holidays.cancellation'

    @api.multi
    def action_save(self):
        context = self.env.context
        if context:
            if 'leave_id' in context:
                if context['leave_id']:
                    leave_id = context['leave_id']
                    leave_obj = self.env['hr.holidays'].browse(leave_id)
                    leave_obj.sudo().write({'cancel_reason':self.reason,'req_cancel':True, 'state': 'waiting_to_cancel'})
        return True