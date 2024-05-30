what=3.10.10
#brew install pyenv
#pyenv install -list # check available versions
#pyenv install $what
pyenv global $what

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"

