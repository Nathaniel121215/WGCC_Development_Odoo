from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT

class TrueMoveHREmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def default_get(self, fields):
        result = super(TrueMoveHREmployee, self).default_get(fields)
        default_country_id = self.env['res.country'].search([('is_default_country','=',True)], limit=1).id
        if default_country_id:
            result['country_id'] = default_country_id
        return result
    
    domain_id = fields.Many2one('hr.domain', string='Domain')

class TrueMoveHRContract(models.Model):
    _inherit = 'hr.contract'

    domain_id = fields.Many2one('hr.domain', string='Domain')
    payroll_type = fields.Selection([('hourly', 'Hourly'), ('daily', 'Daily'), ('monthly', 'Monthly')],
                                    string="Payroll Type")

    # modify action_approve from etsi_hrms because etsi_payroll is not installed
    @api.multi
    def action_approve(self):
        if not self.env.user.has_group('hr.group_hr_manager') and not \
                self.env.user.has_group('etsi_hrms_approvers.group_contract_approver'):
            raise UserError(_('Only an HR Manager can approve contract.'))

        for contract in self:
            res = self.with_context(active_test=False).search([('id', '=', contract.id)])
            values = {
                'active': True,
                'name': contract.name,
                'approval_id': contract.id,
                'employee_id': contract.employee_id.id or False,
                'job_id': contract.job_id.id or False,
                'department_id': contract.department_id.id or False,
                'type_id': contract.type_id.id or False,
                'policy_id': contract.policy_id.id or False,
                'partner_id': contract.partner_id.id or False,
                'wage': contract.wage,
                'struct_id': contract.struct_id.id or False,
                # 'payroll_type': contract.payroll_type,
                # 'cola': contract.cola,
                # 'sss_contri': contract.sss_contri,
                # 'philhealth_contri': contract.philhealth_contri,
                # 'wtax_contri': contract.wtax_contri,
                'date_start': contract.date_start,
                'date_end': contract.date_end,
                'schedule_pay': contract.schedule_pay,
                'leave_policy_type': contract.leave_policy_type,
                'leave_policy_id': contract.leave_policy_id.id or False,
                'working_hours': contract.working_hours.id or False,
            }

            res.write(values)

            emp_ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
            self.env['hr.contract.approver'].create(
                {'employee_id': emp_ids and emp_ids[0].id or False, 'action': 'Approve', 'contract_id': contract.id})

            contract.state = 'open'

    # added autofill of domain and company
    @api.onchange('employee_id')
    def _onchange_employee_id_autofill_domain_and_company(self):
        for rec in self:
            rec.domain_id = rec.employee_id.domain_id.id or False
            rec.partner_id = rec.employee_id.address_id.id or False

class TrueMoveHRHoliday(models.Model):
    _inherit = 'hr.policy.line.absence'

    is_grace_period_monthly = fields.Boolean(string='Monthly Grace Period', default=False)