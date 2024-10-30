# TDS_Project_1
Here , I have Done the web scrapping on Mumbai github users data
# Mumbai GitHub Users Data

This repository contains data on GitHub users in Mumbai with over 50 followers, as well as their public repositories.

## Files

- **users.csv**: Contains information about users, including login, id, URLs, and more.
- **repositories.csv**: Contains information about each repository for the users, including name, description, URLs, and more.

## Data Source

Data was fetched using the [GitHub API](https://docs.github.com/en/rest). Only users in Mumbai with more than 50 followers were included.

## Instructions to Reproduce

1. Set up a GitHub API token and include it in your environment variables.
2. Run the script in this repository to fetch and save data.
3. Generated CSV files will be saved as `users.csv` and `repositories.csv`.
