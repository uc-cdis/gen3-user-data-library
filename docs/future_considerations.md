# Considerations

This file is for notes to be considered regarding the future of this repo

## Malicious links

Currently, it's possible for someone to store malicious links in our db (via the "items") property. 
This is not an issue because they cannot share lists with other users. However, being able to share
lists is a future possible feature. In which case, we should address this issue, perhaps by utilizing a
third party whitelist/blacklist source. 