import os
from dotenv import load_dotenv

from parser.history_parser import DataParser


def main():
    load_dotenv()
    token = os.getenv('TOKEN')
    parser = DataParser(token, "Saudi Arabia Pro League", 'sa')
    parser.parse()


if __name__ == '__main__':
    main()
