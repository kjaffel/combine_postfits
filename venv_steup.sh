
#curl https://pyenv.run | bash
# or 
#brew install pyenv

#pyenv install -list # check available versions
what=3.10.10
#pyenv install $what

pyenv global $what

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"

#pip install -e .
