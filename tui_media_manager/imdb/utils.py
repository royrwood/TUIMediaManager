import asyncio
import json
import re
import dataclasses

from imdbinfo import search_title, get_movie

import aiohttp


@dataclasses.dataclass
class VideoFile:
    file_path: str = ''
    scrubbed_file_name: str = ''
    scrubbed_file_year: str = ''
    imdb_tt: str = ''
    imdb_name: str = ''
    imdb_year: str = ''
    imdb_rating: str = ''
    imdb_genres: list[str] = None
    imdb_plot: str = None
    is_dirty: bool = False


@dataclasses.dataclass
class IMDBInfo:
    imdb_tt: str = ''
    imdb_name: str = ''
    imdb_year: str = ''
    imdb_rating: str = ''
    imdb_genres: list[str] = None
    imdb_plot: str = ''


def scrub_video_file_name(file_name: str, filename_metadata_tokens: str = None) -> tuple[str, str]:
    if filename_metadata_tokens is None:
        filename_metadata_tokens = '480p,720p,1080p,bluray,hevc,x265,x264,web,webrip,web-dl,repack,proper,extended,remastered,dvdrip,dvd,hdtv,xvid,hdrip,brrip,dvdscr,pdtv'

    year = ''

    match = re.match(r'((.*)\((\d{4})\))', file_name)
    if match:
        file_name = match.group(2)
        year = match.group(3)
        scrubbed_file_name_list = file_name.replace('.', ' ').split()

    else:
        metadata_token_list = [token.lower().strip() for token in filename_metadata_tokens.split(',')]
        file_name_parts = file_name.replace('.', ' ').split()
        scrubbed_file_name_list = list()

        for file_name_part in file_name_parts:
            file_name_part = file_name_part.lower()

            if file_name_part in metadata_token_list:
                break
            scrubbed_file_name_list.append(file_name_part)

        if scrubbed_file_name_list:
            match = re.match(r'\(?(\d{4})\)?', scrubbed_file_name_list[-1])
            if match:
                year = match.group(1)
                del scrubbed_file_name_list[-1]

    scrubbed_file_name = ' '.join(scrubbed_file_name_list).strip()
    scrubbed_file_name = re.sub(' +', ' ', scrubbed_file_name)
    return scrubbed_file_name, year


async def get_imdb_basic_info(video_name: str, year: str | None, num_matches: int = 1) -> list[IMDBInfo]:
    # curl -s -H 'Content-Type: application/json' -d @imdb_graphql_simple.json 'https://api.graphql.imdb.com/'

    year = '' if year is None else year

    # This is the GraphQL-- it is not JSON!
    imdb_graphql = f"""
        query {{
          mainSearch(
            first: {num_matches}
            options: {{
              searchTerm: "{video_name} {year}"
              isExactMatch: false
              type: [TITLE]
              titleSearchOptions: {{ type: [MOVIE] }}
            }}
          ) {{
            edges {{
              node {{
                entity {{
                  ... on Title {{
                    __typename
                    id
                    titleText {{ text }}
                    canonicalUrl
                    originalTitleText {{ text }}
                    releaseDate {{ year month day }}
                    primaryImage {{ url }}
                    titleType {{ id text categories {{ id text value }} }}
                    ratingsSummary {{ aggregateRating }}
                    runtime {{ seconds }}
                  }}
                }}
              }}
            }}
          }}
        }}
    """
    # Now pack the GraphQL as a string in a JSON object
    imdb_graphql_json = {'query': imdb_graphql}
    headers = {'Content-Type': 'application/json'}
    url = 'https://api.graphql.imdb.com/'

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=imdb_graphql_json, timeout=30) as imdb_response:
            if imdb_response.status < 200 or imdb_response.status >= 300:
                raise Exception(f'HTTP {imdb_response.status} while fetching search results for {video_name}')
            else:
                imdb_response_text = await imdb_response.text()
                imdb_response_json = json.loads(imdb_response_text)
                edges = imdb_response_json['data']['mainSearch']['edges']
                imdb_info_list = list()
                for edge in edges:
                    edge_node_entity = edge['node']['entity']
                    imdb_info = IMDBInfo()
                    imdb_info.imdb_tt = edge_node_entity['id']
                    imdb_info.imdb_name = edge_node_entity['titleText']['text']
                    imdb_info.imdb_year = str(edge_node_entity['releaseDate']['year'])
                    imdb_info_list.append(imdb_info)
                return imdb_info_list


async def get_imdb_details(imdb_tt: str) -> IMDBInfo:
    movie_details = await asyncio.to_thread(get_movie, imdb_tt)
    imdb_info = IMDBInfo(imdb_tt=imdb_tt,
                         imdb_name=movie_details.title_localized,
                         imdb_year=str(movie_details.year),
                         imdb_rating=str(movie_details.rating),
                         imdb_plot=movie_details.plot,
                         imdb_genres=movie_details.genres)
    return imdb_info


async def search_imdb_title(video_name: str, year: str = '') -> list[IMDBInfo]:
    imdb_search_results = await asyncio.to_thread(search_title, f'{video_name} {year}')

    imdb_info_list = []
    for movie in imdb_search_results.titles:
        imdb_info_list.append(IMDBInfo(imdb_tt=movie.imdb_id, imdb_name=movie.title, imdb_year=movie.year))
    return imdb_info_list

    # imdb_info = IMDBInfo(imdb_tt=imdb_tt,
    #                      imdb_name=movie_details.title_localized,
    #                      imdb_year=str(movie_details.year),
    #                      imdb_rating=str(movie_details.rating),
    #                      imdb_plot=movie_details.plot,
    #                      imdb_genres=movie_details.genres)
    # return imdb_info
