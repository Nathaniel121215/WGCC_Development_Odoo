# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class LoanAmortization(models.Model):
    _name = 'wgcc.amortization'

    name = fields.Many2one('hr.employee', string='name')
    emp_id = fields.Char('employee ID')
    loan_type = fields.Many2one('wgcc.loan.type', string="Loan Type")
    loan_amount = fields.Float('Loan Amount')
    gross_amount = fields.Float('Gross Amount')
    interest_rate = fields.Many2one('interest.rate', string='Interest Rate')
    term_of_months = fields.Integer('Term of Months')

    monthly_payment = fields.Float('Monthly Payment')
    number_of_payment = fields.Integer('No. of Payments')
    total_payment = fields.Integer('Total Payment')
    total_interest = fields.Float('Total Interest')

    share_capital = fields.Float('Share Capital')
    description = fields.Text('Description')
    other_loans = fields.Char('Other Loans') #OPTIONAL: SELECTION FIELD
    amount = fields.Float('Amount')
    savings = fields.Float('Savings')

    description = fields.Text('Description')
    amount = fields.Float('Amount')
   
    preview = fields.Html('')

    @api.onchange('name')
    def _onchange_name(self):
        self.emp_id = self.name.identification_id

    @api.onchange('term_of_months')
    def _onchange_term_of_months(self):
        if self.term_of_months > self.loan_type.maximum_loan_term:
            raise ValidationError("Terms of months should not be greater than maximum term")
        if self.term_of_months < self.loan_type.minimum_loan_term:
             raise ValidationError("Terms of months should not be less than minimum term")

    @api.multi
    def generate_preview(self):
        report_name = 'loan.loan_amortization_report_template'
        report = self.env.ref(report_name)
        if not report:
            raise UserError(_('Report %s not found') % report_name)

        # Get the data to be passed to the report
        docids = self.ids
        docs = self.env['wgcc.amortization'].browse(docids)
        data = {'docs': docs}

        html = report.render(data)
        self.preview = html
        return True
    
    def clear(self):
        self.preview = ""
