from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.http import request
import json
_dtf = '%Y-%m-%d %H:%M:%S'

class TrueMoveHRActualTime(models.Model):
    _inherit = 'hr.actual.time'

    # add domain and filtering for domain and department
    domain_id = fields.Many2one('hr.domain', string='Domain')
    domain_id_domain = fields.Char(compute="_compute_domain_id_domain", readonly=True, store=False)
    department_id_domain = fields.Char(compute="_compute_department_id_domain", readonly=True, store=False)
    employee_id_domain = fields.Char(compute="_compute_employee_id_domain", readonly=True, store=False)

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
    @api.multi
    @api.depends('employee_id')
    def _compute_employee_id_domain(self):
        for record in self:
            user_id = self.env.user.id
            if self.env.user.has_group('etsi_hrms_approvers.group_attn_actual_time_approver'):
                employee_id = self.env['hr.employee'].sudo().search([])
                record.employee_id_domain = json.dumps(
                    [('id', 'in', employee_id.ids)]
                    )
            else:
                employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', user_id)])
            # return [('id', 'in', employee_id.ids)]
                record.employee_id_domain = json.dumps(
                    [('id', 'in', employee_id.ids)]
                    )
            # if record.employee_id:
            #     record.department_id_domain = json.dumps(
            #     [('id', '=', record.employee_id.department_id.id)]
            #     )
    @api.onchange('employee_id')
    def _onchange_employee_id_auto_fill_domain_and_department(self):
        for record in self:
            if record.employee_id:
                record.domain_id = record.employee_id.domain_id.id
                record.department_id = record.employee_id.department_id.id
    # add domain and filtering for domain and department - END

    # modify action_confirm of etsi_attendance module that causes boolean error, added if conditions for line_attendance_checkin and actual_datetime
    @api.multi
    def action_confirm(self):
        # print 'HEYY confirm 2222'
        actual_time_id = self
        line_ids = self.mapped('actual_time_line_ids')
        # print 'line_ids',line_ids
        # for line in line_ids:
        #     line_attendance_checkin = False
        #     if line.attendance_id.check_in:
        #         line_attendance_checkin = datetime.strptime(line.attendance_id.check_in,_dtf)
        #     # print 'line.attendance_id.check_in',line.attendance_id.check_in
        #     actual_datetime = False
        #     if line.actual_time and line.date:
        #         actual_datetime = line.convert_float_to_local_time(line.actual_time, line.date)
        #     if line_attendance_checkin and actual_datetime:
        #         attendance_obj = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
        #                                                         ('check_out','<=',datetime.strftime(actual_datetime, _dtf)),
        #                                                         ('check_in','>=',datetime.strftime(line_attendance_checkin, _dtf))])
        #         # print 'attendance_obj',attendance_obj
        #         for att in attendance_obj:
        #             raise UserError(
        #                         _('You cannot modify a log or attendance that overlaps or already exists.\n '
        #                         'Please review your request. (%s)' % (str(datetime.strptime(att.check_in,_dtf).date()))))
        time_sheet = self.env['hr_timesheet_sheet.sheet'].search([('employee_id','=',self.employee_id.id)])
        list_of_dates = []
        for record in self.mapped('actual_time_line_ids'):
            if record.mode == 'add':
                list_of_dates.append(record.chkin_date)
            elif record.mode == 'change':
                list_of_dates.append(record.date)
            else:
                check_in = datetime.strptime(record.check_in,DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                list_of_dates.append(check_in)
        if list_of_dates:
            start_date = min(list_of_dates)
            end_date = max(list_of_dates)
            timesheet = time_sheet.filtered(lambda x:x.date_from <= start_date and x.date_to >= end_date )

            # if timesheet.state in ['done','confirm']:
            #     raise ValidationError("You cannot modify an attendance in a submitted timesheet. Ask your manager to reset it before modifying the attendance.")
            if timesheet.state in ['confirm']:
                raise ValidationError("You cannot modify an attendance in a submitted timesheet. Ask your manager to reset it before modifying the attendance.")
            if timesheet.state in ['done']:
                raise ValidationError("You cannot modify an attendance in an approved timesheet.  Ask your manager to reset it before modifying the attendance.")
                # for rec in attendance_obj:
                #


        if self.employee_id.user_id.id != self.env.uid:
            requester_id = self.env['hr.employee'].search([('id', '=', self.employee_id.id)])
            dept = requester_id.department_id.name
            email_cc = requester_id.parent_id.name
        else:
            requester_id = self.env['res.users'].browse(self.env.uid)
            user_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
            dept = user_id.department_id.name
            # email_cc = user_id.parent_id.work_email
        # Get Approvers Data
        # desc = values['name']
        user_recs = self.env['res.users'].search([])
        email_to_rec = ""
        department_user_id = self.department_id.manager_id.user_id.id
        for rec in user_recs:
            if rec.has_group('etsi_hrms_approvers.group_attn_actual_time_approver'):
                if department_user_id:
                    if rec.id == department_user_id:
                        email_to_rec += str(rec.partner_id.email) + ','
        # If Multiple Recipients
        approver = email_to_rec.split(',')
        if len(approver) > 2 or not email_to_rec:
            first_approver = "Sir/Ma'am"
        else:
            first_approver = "Sir/Ma'am %s"%(self.env['res.users'].search([('login', '=', approver)]).name)

        # Send Link
        actualtime_request_menu = self.env['ir.model.data'].sudo().get_object('etsi_attendance','menu_actual_time_requests')
        actualtime_request_action = self.env['ir.model.data'].sudo().get_object('etsi_attendance','actual_time_action')
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s&menu_id=%d&action=%d' % (
            actual_time_id.id, self._name, actualtime_request_menu,
            actualtime_request_action)
        # Send Email Notification

        values = {}
        #values.update({'name': 'Actual Time Request'})
        values.update({'subject': 'Actual Time Request'})
        values.update({'email_from': self.env['res.users'].browse(self.env.uid).company_id.email})
        values.update({'email_to': email_to_rec})
        # values.update({'email_cc': email_cc})
        values.update({'auto_delete': True})
        values.update(
            {'body_html': "<br/>Dear  <b>%s,</b>" % first_approver
                          + "<br/><br/> Actual time request of <b>%s</b>" % requester_id.name
                          + " is pending for your approval. <br/><br/>"
                          # + "<ul><li>Leave Description: %s <br/><br/></li></ul>" % desc
                          + "<p><a href='%s' style='padding:8px 12px; font-size:12px; color:#FFFFFF; text-decoration: none !important;font-weight: 400;background-color: #875A7B;border: 0px solid #875A7B;border-radius: 3px'>View actual time request</a></p><br/>" % base_url
                          + "Regards, <br/>"
                          + "%s Department" % dept
             })
        send_mail = self.env['mail.mail'].create(values)
        send_mail.send(True)
        self.state = 'confirm'