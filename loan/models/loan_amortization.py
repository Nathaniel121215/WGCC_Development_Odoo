# -- coding: utf-8 --

from odoo import _, api, fields, models

class LoanAmortization(models.Model):
    _name = 'wgcc.amortization'

    employee_id = fields.Many2one('hr.employee', string='employee')
    name = fields.Char('name', required=True)
    loan_type = fields.Selection([
        ('BUSINESS ASSISTANCE LOAN','BUSINESS ASSISTANCE LOAN'),
        ('COMMERCIAL LOAN','COMMERCIAL LOAN'),
        ('PERSONAL LOAN','PERSONAL LOAN'), #accounting module
    ], string='Loan Type') #OPTIONAL: ONE2MANY FIELD
    loan_amount = fields.Float('Loan Amount')
    gross_amount = fields.Float('Gross Amount')
    interest_rate = fields.Float('Interest Rate')
    term_of_months = fields.Integer('Term of Months')

    monthly_payment = fields.Float('Monthly Payment')
    number_of_payment = fields.Integer('No. of Payments')
    total_payment = fields.Integer('Total Payment')
    total_interest = fields.Float('Total Interest')

    share_capital = fields.Float('Share Capital')
    description = fields.Text('Description')
    other_loans = fields.Char('Other Loans') #OPTIONAL: SELECTION FIELD
    amount = fields.Float('Amount')

    description = fields.Text('Description')
    amount = fields.Float('Amount')
   
