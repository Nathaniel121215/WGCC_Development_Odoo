# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class LoanApplication(models.Model):
    _name = 'wgcc.loanapplication'

    # Member's Information
    employee_id = fields.Integer('Employee ID No:')
    employee_name = fields.Char('Name:')
    company_name = fields.Char('Company:')

    date_hired = fields.Date('Date Hired:')
    years_in_service = fields.Many2one('years.service',string="Years in Service:")
    membership_date = fields.Date('Membership Date:')

    pms_date = fields.Date('PMS Date:')
    share_capital_balance = fields.Float('Share Capital Balance:')

    billing_l_6month = fields.Float('Billing for the last 6 months:')
    collection_l_6month = fields.Float('Collection last 6 months:')
    class_type = fields.Many2one('class.type',string="Class:")
    collection_percentage = fields.Char('Collection %:')
    employee_salary = fields.Char('Salary:')

    # Details of Loan
    loan_no = fields.Integer('Loan No:')
    loan_type = fields.Many2one('loan.type',string="Loan Type:")
    loan_amount = fields.Float('Loan Amount')
    terms_in_mos = fields.Many2one('terms.mos',string="Terms in Mos:")
    monthly_armotization = fields.Float('Monthly Armortization:')

    semi_armotization = fields.Float('Semi Monthly Armortization:')
    interest = fields.Float('Interest:')
    principal = fields.Float('Principal:')
    payment_option = fields.Many2one('payment.option',string="Payment Option:")
    release_option = fields.Many2one('release.option',string="Release Option:")

    # Co - Makers
    comakers_table = fields.One2many('co.makers','comaker_con')

    # Previous Loan
    previous_loan_no = fields.Integer('Loan No:')
    previous_loan_type = fields.Many2one('loan.type',string="Loan Type:")
    previous_gross_amount = fields.Float('Gross Amount:')
    previous_released_date = fields.Date('Released Date:')
    previous_existing_balance = fields.Float('Existing Balance:')
    previous_deferred_balance = fields.Float('Deferred Balance:')
    previous_terms_in_mos = fields.Many2one('terms.mos',string="Terms in Mos:")
    previous_monthly_armotization = fields.Float('Monthly Amortization:')

    encoded_by = fields.Char('Encoded By:')
    date_encoded = fields.Date('Date Encoded:')

class LoanApplicationTermsinMos(models.Model):
    _name = 'terms.mos'

    terms_in_mos = fields.Char('Terms in Mos:')

class LoanApplicationPaymentOption(models.Model):
    _name = 'payment.option'

    payment_option = fields.Char('Payment Option:')

class LoanApplicationReleaseOption(models.Model):
    _name = 'release.option'

    release_option = fields.Char('Release Option:')

class LoanApplicationLoanType(models.Model):
    _name = 'loan.type'

    loan_type = fields.Char('Loan Type:')

class LoanApplicationClassType(models.Model):
    _name = 'class.type'

    class_type = fields.Char('Class Type:')

class LoanApplicationYearsofService(models.Model):
    _name = 'years.service'

    years_in_service = fields.Integer('Years in Service:')

class LoanApplicationCoMakers(models.Model):
    _name = 'co.makers'

    comaker_con = fields.Many2one('wgcc.loanapplication')
    comakers_id = fields.Integer('ID No:')
    comakers_name = fields.Char('Name:')
    comakers_contact = fields.Integer('Contact No:')
    comakers_Address = fields.Char('Address:')
  