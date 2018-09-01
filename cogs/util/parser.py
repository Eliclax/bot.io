# Is this overkill, probably. Is it fun, yes!

SYMBOL, NUMBER, STRING, IDENTIFIER, EOF = ('symbol', 'number', 'string', 'identifier', 'EOF')


class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __eq__(self, x):
        if self.type != SYMBOL: return False
        return self.value == x

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self.__str__()


class ParserException(BaseException):
    pass


class Lexer:
    NAME_START_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_'
    NAME_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789'
    STRING_DELIM = '\'"'

    SINGLE_CHARS = '()=,'

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.current_char = self.text[self.pos]

    # Utils
    def error(self):
        print(self.current_char)
        raise ParserException('Invalid character')

    def advance(self):
        self.pos += 1
        if self.pos > len(self.text) - 1:
            self.current_char = None  # Indicates end of input
        else:
            self.current_char = self.text[self.pos]

    def peek(self):
        if self.pos + 1 > len(self.text) - 1:
            return None
        return self.text[self.pos + 1]

    # Types
    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def integer(self):
        result = ''
        while self.current_char is not None and (self.current_char.isdigit() or (self.current_char == '.' and '.' not in result)):
            result += self.current_char
            self.advance()
        if '.' in result:
            return float(result)
        return int(result)

    def var_name(self):
        result = ''
        while self.current_char is not None and self.current_char in self.NAME_CHARS:
            result += self.current_char
            self.advance()
        return result

    def string(self):
        result = ''
        opened_with = self.current_char
        self.advance()
        while True:
            result += self.current_char
            self.advance()

            if self.current_char == opened_with:
                if result.endswith('\\'):
                    result = result[:-1]
                    continue
                break
        self.advance()
        return result

    # Tokenizer
    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            if self.current_char in self.SINGLE_CHARS:
                char = self.current_char
                self.advance()
                return Token(SYMBOL, char)
            if self.current_char.isdigit():
                return Token(NUMBER, self.integer())
            if self.current_char in self.STRING_DELIM:
                return Token(STRING, self.string())
            if self.current_char in self.NAME_START_CHARS:
                vn = self.var_name()
                return Token(IDENTIFIER, vn)

            self.error()

        return Token(EOF, None)


class Parser:
    def __init__(self, lexer):
        # Tokenize the entire file
        self.tokens = []
        current_token = lexer.get_next_token()
        while current_token.type != EOF:
            self.tokens.append(current_token)
            current_token = lexer.get_next_token()
        self.tokens.append(current_token)

        self.pos = 0
        self.current_token = self.tokens[self.pos]

    def error(self, token, value=None):
        if token is None:
            token = 'EOF'
        if token == SYMBOL:
            token = f'"{value}"'
        curr = f'"{self.current_token}"' if self.current_token.value is not None else 'EOF'
        raise ParserException(f'Invalid Syntax. Expected `{token}`, got `{curr}`.')

    def peek(self):
        next_pos = min(len(self.tokens) - 1, self.pos + 1)
        return self.tokens[next_pos]

    def eat(self, token_type, value=None):
        if self.current_token.type == token_type and (value is None or self.current_token.value == value):
            self.pos = min(len(self.tokens) - 1, self.pos + 1)
            self.current_token = self.tokens[self.pos]
        else:
            self.error(token_type, value)

    def value(self):
        if self.current_token.type in [NUMBER, STRING]:
            v = self.current_token.value
            self.eat(self.current_token.type)
        else:
            self.error('literal')

        return v

    def params(self):
        items = []
        self.eat(SYMBOL, '(')
        while self.current_token != ')':
            items.append(self.value())
            if self.current_token != ')':
                self.eat(SYMBOL, ',')
        self.eat(SYMBOL, ')')

        return items

    def eof_params(self):
        items = []

        parens = False
        if self.current_token == '(':
            parens = True
            self.eat(SYMBOL, '(')

        while True:
            items.append(self.value())
            if not parens:
                if self.current_token.type != EOF:
                    self.eat(SYMBOL, ',')
                else:
                    break
            else:
                if self.current_token != ')':
                    self.eat(SYMBOL, ',')
                else:
                    self.eat(SYMBOL, ')')
                    break
        return items

    def query(self):
        name = self.current_token.value
        self.eat(IDENTIFIER)
        params = self.params()

        if self.current_token == '=':
            self.eat(SYMBOL, '=')
            guess = self.eof_params()
        else:
            guess = None

        self.eat(EOF)

        return [name, params, guess]


def parse(query):
    parser = Parser(Lexer(query))

    try:
        return True, parser.query()
    except ParserException as e:
        return False, str(e)
