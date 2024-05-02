import os.path
import requests
import json
import logging


class DataParser:
    sport_id = 1
    per_page = 100

    def __init__(self, token, league_name, cc):
        self.token = token
        self.league_name = league_name
        self.cc = cc
        self.logger = logging.getLogger(__name__)
        self.logger = self.__setup_logger()
        self.__init_directory()
        self.__find_league_id()


    def __init_directory(self):
        directory = f"data_{self.league_name}"
        if not os.path.exists(directory):
            os.makedirs(directory)
            self.logger.info(f"New directory created {directory}")

        self.directory = directory


    def __setup_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler('data_parser.log')
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def __get_leagues(self):
        params = {
            'token': self.token,
            'sport_id': self.sport_id,
            'cc': self.cc
        }
        url = 'https://api.b365api.com/v1/league'

        response = requests.get(url=url, params=params)

        if response.status_code == 200:
            self.logger.debug("200 received from betsAPI")
            return response.json()
        else:
            self.logger.error("Failed to fetch leagues data. Status code: %s", response.status_code)
            return None


    def __find_league_id(self):
        data = self.__get_leagues()
        leagues = data["results"]

        for league in leagues:
            if league["name"] == self.league_name:
                self.league_id = int(league["id"])
                self.logger.info(f"Get league: {self.league_name} id: {self.league_id}")



    def __get_league_table(self):
        params = {
            'token': self.token,
            'league_id': self.league_id
        }
        url = 'https://api.b365api.com/v3/league/table'

        response = requests.get(url=url, params=params)

        if response.status_code == 200:
            self.logger.debug("200 received from betsAPI")
            return response.json()
        else:
            self.logger.error("Failed to fetch league table data. Status code: %s", response.status_code)
            return None

    def __find_teams_ids(self):
        data = self.__get_league_table()
        table = data["results"][0]["overall"]["tables"][0]["rows"]
        teams_ids = {}
        for row in table:
            name = row["team"]["name"]
            team_id = row["team"]["id"]

            teams_ids[name] = team_id

        self.teams = teams_ids
        self.logger.info(f"Get teams {self.teams}")



    def __get_team_matches(self, team_id, page):
        params = {
            'token': self.token,
            'sport_id': self.sport_id,
            'team_id': team_id,
            'per_page': self.per_page,
            'page': page
        }
        url = 'https://api.b365api.com/v3/events/ended'

        response = requests.get(url=url, params=params)

        if response.status_code == 200:
            self.logger.debug("200 received from betsAPI")
            return response.json()
        else:
            self.logger.error("Failed to fetch matches data. Status code: %s", response.status_code)
            return None

    def __get_odds_for_match(self, event_id):
        params = {
            'token': self.token,
            'event_id': event_id
        }
        url = 'https://api.b365api.com/v2/event/odds'

        response = requests.get(url=url, params=params)

        if response.status_code == 200:
            self.logger.debug("200 received from betsAPI")
            return response.json()
        else:
            self.logger.error("Failed to fetch odds data. Status code: %s", response.status_code)
            return None

    def __write_odds_for_match(self, team_name, team_id):
        output_filename = f"{self.directory}//event_odds_{team_name}_{team_id}.json"
        with open(output_filename, "w") as file:
            self.logger.debug(f"File opened {output_filename}")
            file.write("[")
            page = 1
            while True:
                data = self.__get_team_matches(team_id, page)
                matches = data['results']
                if len(matches) == 0:
                    break
                for i, match in enumerate(matches):
                    match_data = self.__extract_match_data(match)
                    if match_data:
                        self.__write_match_data(file, match_data, page == 1 and i == 0)
                        self.logger.debug("New match added")
                page += 1
            file.write("]")
        self.logger.debug("File closed")

    def __extract_match_data(self, match):
        event_id = match["id"]
        home_team_name, home_team_id = match["home"]["name"], match["home"]["id"]
        away_team_name, away_team_id = match["away"]["name"], match["away"]["id"]
        odds_data = self.__get_odds_for_match(event_id)
        odds = odds_data["results"]["odds"]
        if odds:
            self.logger.debug(f"Match extracted {home_team_name}-{away_team_name}")
            return {
                "home": {
                    "id": home_team_id,
                    "name": home_team_name
                },
                "away": {
                    "id": away_team_id,
                    "name": away_team_name
                },
                "odds": odds
            }
        else:
            self.logger.debug(f"No odds for match {home_team_name}-{away_team_name}")
            return None

    def __write_match_data(self, file, match_data, is_first_match):
        if not is_first_match:
            file.write(",")
        json.dump(match_data, file)

    def __iterate_teams(self):
        for team_name, team_id in self.teams.items():
            self.logger.debug("Get matches and odds for %s", team_name)
            self.__write_odds_for_match(team_name, team_id)


    def parse(self):
        self.logger.info(f"Parsing started league: {self.league_name}")
        self.__find_teams_ids()
        # name = next(iter(self.teams))
        # team_id = self.teams[name]
        # self.__write_odds_for_match(name, team_id)
        self.__iterate_teams()
        self.logger.info("Finished")
