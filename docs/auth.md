# What are token claims?

Claim is a term as a part of a token. Our token uses public private encryption. Fence has both keys and 
the ability to sign a token as well as provide a user. Fence is the owner of the private keys. 

On the server side, we decode the token content to ensure it has not been modified using fence. 
If The token has not been modified, we return the token contents encoded in json base 64. The "sub"
field is required by oauth, sub is a shortening of subject. Our use case is to get the unique 
subject id. 
