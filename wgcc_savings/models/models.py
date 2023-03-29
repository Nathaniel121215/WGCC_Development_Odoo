# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from num2words import num2words
from odoo.exceptions import ValidationError, UserError

class wgcc_savings(models.Model):
    _name = 'wgcc_savings.wgcc_savings'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    
    employee_id = fields.Many2one('hr.employee', string="Employee ID No.", create=False)
    name = fields.Char(string="Name:")
    search_field = fields.Char(string="Search:")
    deposit_amount = fields.Float(string='Deposit Amount', digits=(10, 2), required=True)

    deposit_date = fields.Date(string='Deposit Date', default=datetime.now(),required=True)
    Company = fields.Many2one('res.company',string="Company")
    current_balance_before_widthrawal = fields.Float(string='Current Balance Before Widthrawal: ', digits=(10, 2))
    last_date_of_widthrawal = fields.Date(string='Last Date Of Widthrawal')
    saving_deposit_deduction = fields.Float(string='Savings Deposit Deduction')
    withdrawable_balance = fields.Float(string='Withdrawable Balance', digits=(10, 2))
    account_number = fields.Char(string="Account Number:")
    bank_code = fields.Char(string="Bank Code:")
    withdrawable_mode = fields.Selection([
        ('cash', 'CASH'),
        ('atm', 'ATM'),
        ('cheque', 'Cheque'),
        
    ], string='Withdrawal Mode', default="cash", required=True)
    amount_to_be_widthrawn = fields.Float(string='Amount to be withdrawn: ', digits=(10, 2), required=True)
    withdrawal_slip_no = fields.Char(string='Withdrawal Slip No.', readonly=True, copy=False)
    cash = fields.Char(string="Cash (Words)")
    date_of_widthrawal = fields.Date(string='Date Of Widthrawal:',default=datetime.now())
    is_atm = fields.Boolean(string="ATM")
    release_date = fields.Date(string='Release Date',default=datetime.now())
    is_cheque = fields.Boolean(string="Check")
    cheque_information = fields.Char("Cheque Information: ")
    bank = fields.Many2one('res.bank', string="Bank")
    cheque_no = fields.Char("Cheque No: ")
    prepared_by = fields.Many2one('hr.employee', string="Prepared By",  create=False)
    posted_by = fields.Many2one('hr.employee', string="Posted By",  create=False)
    cancelled_by = fields.Many2one('hr.employee', string="Cancelled By",  create=False)
    cancel_reason = fields.Char("Cancel Reason",  create=False)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('released', 'Released'),
        ('cancelled', 'Cancelled'),
        
    ], string='Status', readonly="True", default="draft")
    
    current_user = fields.Many2one('res.users','Current User', default=lambda self: self.env.user.id) 
    cancelled = fields.Boolean(string="Cancelled")
    @api.multi
    def custom_release(self):

        self.update({'status': 'released'})
        self.update({'posted_by': self.current_user.id})
        
    @api.multi
    def custom_cancel(self):
        
        if self.cancel_reason:
            self.update({'status': 'cancelled'})
            self.update({'cancelled_by': self.current_user.id})
        else:
            raise ValidationError("Please provide a cancel reason")
        
    @api.onchange('amount_to_be_widthrawn')
    def amount_to_word(self):
        amount = num2words(self.amount_to_be_widthrawn)
        
        if self.amount_to_be_widthrawn > 0.00:
            self.update({ 'cash' : amount.capitalize() + " " + "Pesos"})
            
    field_one2many = fields.One2many('table_name', 'connector' )
# Sequence 
    @api.model
    def create(self, vals):
        
        self.update({'prepared_by': self.current_user.id})
        if vals.get('withdrawal_slip_no', 'New') == 'New':
            vals['withdrawal_slip_no'] = self.env['ir.sequence'].next_by_code('withdrawal_slip_no_seq')  or 'New'
    
        return super(wgcc_savings, self).create(vals)

    @api.onchange('employee_id', 'withdrawable_mode', 'cheque_information','cheque_no')
    def employee_id_search(self):
        database = self.env['hr.employee']
        if self.employee_id:
            
            cheque_information = self.cheque_information
            cheque_no = self.cheque_no
            
            
            search = database.search([('id', '=', self.employee_id.id)])
        
            for item in search:
                if self.withdrawable_mode == "atm":
                    print("Na dtetct ko naman na ATM ")
                    print("Na dtetct ko naman na ATM ")
                    print("Na dtetct ko naman na ATM ")

                    self.update({'Company': item.company_id.id,
                                'bank' : item.bank_name.id,
                                'account_number' :  item.bank_acc_number,
                                'bank_code' : item.bank_name.bic
                                })
                else:
                    
                    print( cheque_information, "Cheque Information")
                    print( cheque_no, "Cheque No")
                    
                    self.update({'bank': False,
                                'account_number' :  False,
                                'bank_code' : False
                                 })
                    
               
                
                if self.withdrawable_mode != "cheque":
                    self.update({'cheque_information': False,
                                'cheque_no' :  False
                                 })
                else:
                    self.update({'cheque_information': cheque_information,
                                'cheque_no' :  cheque_no
                                 })
               
class Membership_Inherit(models.Model):
    _inherit = "hr.employee"
        
class Sample(models.Model):
    _name = 'table_name'
    
    
    name= fields.Char("Name 1")
    name2= fields.Char("Name 2")
    name3= fields.Char("Name 3")
    name4= fields.Char("Name 4")
    name5= fields.Char("Name 5")
    name6= fields.Char("Name 6")

    connector = fields.Many2one('wgcc_savings.wgcc_savings',  create=False)
    
    
#     # # One2many lists
# class wgcc_membership(models.Model):
#     _name = 'wgcc_membership.wgcc_membership'
    
#     name = fields.Char("Name")
#     employee_id =fields.Many2one('hr.employee',  create=False)
    
#     savings_deposit = fields.One2many('savings_deposit_module', 'main_model_id' )
#     share_capital = fields.One2many('share_capital_module', 'share_model_id')
#     loan_balances = fields.One2many('loan_balance_module', 'loan_balance_model_id')
    
#     @api.multi
#     def search_member(self):
        
#         print("MEMBER")
           
    
# class Savings_Deposit(models.Model):
#     _name = 'savings_deposit_module'

#     date = fields.Date(string="Date")
#     reference_no = fields.Char("Reference No.")
#     slip_no = fields.Char("Slip No.")
#     deposit = fields.Float(string='Deposit', digits=(10, 2))
#     widthrawal = fields.Float(string='Widthrawal', digits=(10, 2))
#     balance = fields.Float(string='Balance', digits=(10, 2))
#     lmb = fields.Char("LMB")
    
    
#     main_model_id = fields.Many2one('wgcc_membership.wgcc_membership', string='Main Model',  create=False)    
    
# class Share_Capital(models.Model):
#     _name = 'share_capital_module'
    
#     # name = fields.Char("Name")
    
#     date = fields.Date(string="Date")
#     reference_no = fields.Char("Reference No.")
#     debit = fields.Float(string='Debit', digits=(10, 2))
#     credit = fields.Float(string='Credit', digits=(10, 2))
#     balance = fields.Float(string='Balance', digits=(10, 2))
#     share_model_id = fields.Many2one('wgcc_membership.wgcc_membership', string='Main Model',  create=False) 

# class Loan_Balance(models.Model):    
#     _name = 'loan_balance_module'
    
#     name = fields.Char("Name")
#     loan_type = fields.Selection([
#         ('buena', 'Buena Mano Loan'),
#         ('calamity', 'Calamity Loan'),])
#     loan_no = fields.Char("Loan No.")
#     gross_amount = fields.Float(string='Gross Amount', digits=(10, 2))
    
#     terms = fields.Char("Terms")
#     monthly_amortization = fields.Float(string='Monthly Amortization', digits=(10, 2))
#     balance = fields.Float(string='Balance', digits=(10, 2))
#     date_released = fields.Date(string="Date Released")
#     deferred = fields.Char("Deferred")
#     date_as_of = fields.Date(string="Date As of")
#     loan_balance_model_id = fields.Many2one('wgcc_membership.wgcc_membership', string='Loan Balance ID',  create=False)
