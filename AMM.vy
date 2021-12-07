from vyper.interfaces import ERC20

tokenAQty: public(uint256) #Quantity of tokenA held by the contract
tokenBQty: public(uint256) #Quantity of tokenB held by the contract

invariant: public(uint256) #The Constant-Function invariant (tokenAQty*tokenBQty = invariant throughout the life of the contract)
tokenA: ERC20 #The ERC20 contract for tokenA
tokenB: ERC20 #The ERC20 contract for tokenB
owner: public(address) #The liquidity provider (the address that has the right to withdraw funds and close the contract)

@external
def get_token_address(token: uint256) -> address:
	if token == 0:
		return self.tokenA.address
	if token == 1:
		return self.tokenB.address
	return ZERO_ADDRESS	

# Sets the on chain market maker with its owner, and initial token quantities
@external
def provideLiquidity(tokenA_addr: address, tokenB_addr: address, tokenA_quantity: uint256, tokenB_quantity: uint256):
	assert self.invariant == 0 #This ensures that liquidity can only be provided once
  
	#Your code here
	self.owner=msg.sender
	self.tokenA=ERC20(tokenA_addr)
	self.tokenB=ERC20(tokenB_addr)
	self.tokenA.transferFrom(msg.sender,self,tokenA_quantity)
	self.tokenB.transferFrom(msg.sender,self,tokenB_quantity)
	self.tokenAQty=tokenA_quantity
	self.tokenBQty=tokenB_quantity
	self.invariant=tokenA_quantity*tokenB_quantity  
  
	assert self.invariant > 0

# Trades one token for the other
@external
def tradeTokens(sell_token: address, sell_quantity: uint256):
	assert sell_token == self.tokenA.address or sell_token == self.tokenB.address
  
	#Your code here
	assert sell_quantity>0
	ratio: uint256=0
	ratio= self.tokenAQty/self.tokenBQty
  
	if (self.invariant==0):
		ratio=1
    
	if (sell_token==self.tokenA.address):
		#returnAmount: uint256=0
		#returnAmount=sell_quantity*ratio	

		self.tokenA.transferFrom(msg.sender,self,sell_quantity)
		self.tokenB.transfer(msg.sender,sell_quantity)
		self.tokenBQty-=sell_quantity
		self.tokenAQty+=sell_quantity
	else:
		#returnAmount: uint256=0
		#returnAmount=sell_quantity/ratio	

		self.tokenB.transferFrom(msg.sender,self,sell_quantity)
		self.tokenA.transfer(msg.sender,sell_quantity)
		self.tokenAQty-=sell_quantity
		self.tokenBQty+=sell_quantity

# Owner can withdraw their funds and destroy the market maker
@external
def ownerWithdraw():
    assert self.owner == msg.sender
    
	#Your code here
    self.tokenA.transfer(self.owner,self.tokenAQty)
    self.tokenB.transfer(self.owner,self.tokenBQty)
    self.tokenAQty=0
    self.tokenBQty=0
    selfdestruct(self.owner)