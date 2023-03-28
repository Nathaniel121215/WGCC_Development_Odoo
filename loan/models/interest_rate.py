from odoo import _, api, fields, models

class InterestRate(models.Model):
    _name = 'interest.rate'
    _description = 'interest.rate'
    _rec_name = 'interest_rate'
    
    interest_rate = fields.Float('Interest Rate')