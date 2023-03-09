# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class LoanAmortization(models.Model):
    _name = 'wgcc.amortization'

    employee_id = fields.Integer('Employee ID')
    name = fields.Char('name')
    loan_type = fields.Selection([
        ('loan1', 'Loan1')
    ], string='loan_type')
    loan_amount = fields.Float('Loan Amount')
    gross_amount = fields.Float('Gross Amount')
    interest_rate = fields.Float('Interest Rate')
    term_of_months = fields.Integer('Term of Months')

    monthly_payment = fields.Float('Monthly Payment')
    number_of_payment = fields.Integer('No. of Payments')
    total_payment = fields.Integer('Total Payment')
    total_interest = fields.Float('Total Interest')

    share_capital = fields.Float('Share Capital')
    description = fields.Char('Description')
    other_loans = fields.Char('Other Loans')
    amount = fields.Float('Amount')

