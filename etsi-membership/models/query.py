from odoo import api, fields, models, _

# One2many lists
class wgcc_membership(models.Model):
    _name = 'wgcc_membership.wgcc_membership'
    
    name = fields.Char("Name")
    employee_id =fields.Many2one('hr.employee',  create=False)
    
    savings_deposit = fields.One2many('savings_deposit_module', 'main_model_id' )
    share_capital = fields.One2many('share_capital_module', 'share_model_id')
    loan_balances = fields.One2many('loan_balance_module', 'loan_balance_model_id')
    
    @api.multi
    def search_member(self):
        print("MEMBER")
    
class Savings_Deposit(models.Model):
    _name = 'savings_deposit_module'

    date = fields.Date(string="Date")
    reference_no = fields.Char("Reference No.")
    slip_no = fields.Char("Slip No.")
    deposit = fields.Float(string='Deposit', digits=(10, 2))
    widthrawal = fields.Float(string='Widthrawal', digits=(10, 2))
    balance = fields.Float(string='Balance', digits=(10, 2))
    lmb = fields.Char("LMB")
    
    
    main_model_id = fields.Many2one('wgcc_membership.wgcc_membership', string='Main Model',  create=False)    
    
class Share_Capital(models.Model):
    _name = 'share_capital_module'
    
    # name = fields.Char("Name")
    
    date = fields.Date(string="Date")
    reference_no = fields.Char("Reference No.")
    debit = fields.Float(string='Debit', digits=(10, 2))
    credit = fields.Float(string='Credit', digits=(10, 2))
    balance = fields.Float(string='Balance', digits=(10, 2))
    share_model_id = fields.Many2one('wgcc_membership.wgcc_membership', string='Main Model',  create=False) 

class Loan_Balance(models.Model):    
    _name = 'loan_balance_module'
    
    name = fields.Char("Name")
    loan_type = fields.Selection([
        ('buena', 'Buena Mano Loan'),
        ('calamity', 'Calamity Loan'),])
    loan_no = fields.Char("Loan No.")
    gross_amount = fields.Float(string='Gross Amount', digits=(10, 2))
    
    terms = fields.Char("Terms")
    monthly_amortization = fields.Float(string='Monthly Amortization', digits=(10, 2))
    balance = fields.Float(string='Balance', digits=(10, 2))
    date_released = fields.Date(string="Date Released")
    deferred = fields.Char("Deferred")
    date_as_of = fields.Date(string="Date As of")
    loan_balance_model_id = fields.Many2one('wgcc_membership.wgcc_membership', string='Loan Balance ID',  create=False)