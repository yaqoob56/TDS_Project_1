import requests
import pandas as pd
import os
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np

# Set your GitHub token here (please do not expose your token publicly)
GITHUB_TOKEN = "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"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def fetch_users(city="Mumbai", min_followers=50):
    """Fetch GitHub users based on location and minimum followers."""
    users = []
    page = 1
    while True:
        url = f"https://api.github.com/search/users?q=location:{city}+followers:>{min_followers}&per_page=100&page={page}"
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            users.extend(data.get("items", []))
            print(f"Fetched {len(users)} users so far from page {page}")
            
            # Check if there are more pages
            if "next" not in response.links:
                break
            page += 1
        except requests.RequestException as e:
            print(f"Error fetching users: {e}")
            break
    return users

def fetch_repositories(username):
    """Fetch all repositories for a given GitHub user."""
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            repos_data = response.json()
            if not repos_data:
                break
            repos.extend(repos_data)
            page += 1
        except requests.RequestException as e:
            print(f"Error fetching repositories for {username}: {e}")
            break
    return repos

def clean_company_name(company):
    """Clean company name by stripping and formatting."""
    return company.strip().lstrip('@').upper() if company else ""

def prepare_data(users):
    """Prepare a list of user and repository data."""
    users_list = []
    repos_list = []

    for user in users:
        user_data = {
            "login": user["login"],
            "name": user.get("name", ""),
            "company": clean_company_name(user.get("company", "")),
            "location": user.get("location", ""),
            "email": user.get("email", ""),
            "hireable": user.get("hireable", False),
            "bio": user.get("bio", ""),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "created_at": user.get("created_at", "")
        }
        users_list.append(user_data)

        # Fetch repositories for the user
        repos = fetch_repositories(user["login"])
        for repo in repos:
            license_name = repo.get("license", {}).get("name", "") if repo.get("license") else ""

            repos_data = {
                "login": user["login"],
                "full_name": repo["full_name"],
                "created_at": repo["created_at"],
                "stargazers_count": repo.get("stargazers_count", 0),
                "watchers_count": repo.get("watchers_count", 0),
                "language": repo.get("language", ""),
                "has_projects": repo.get("has_projects", False),
                "has_wiki": repo.get("has_wiki", False),
                "license_name": license_name
            }
            repos_list.append(repos_data)

    return users_list, repos_list

def create_csv_files(users, repos):
    """Create CSV files from users and repositories data."""
    users_df = pd.DataFrame(users)
    repos_df = pd.DataFrame(repos)

    users_df.to_csv("users.csv", index=False)
    repos_df.to_csv("repositories.csv", index=False)

def analyze_data(users, repos):
    recent_users = []
    for user in users:
        created_at = user.get('created_at', '')
        if created_at:  # Check if created_at is not empty
            try:
                user_year = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").year
                if user_year > 2020:
                    recent_users.append(user)
            except ValueError:
                print(f"Invalid date format for user: {user.get('login', 'Unknown')}, created_at: {created_at}")
        else:
            print(f"Empty created_at for user: {user.get('login', 'Unknown')}")  # Debug information

    # 1. Top 5 users by followers
    top_users = sorted(users, key=lambda x: x['followers'], reverse=True)[:5]
    top_users_logins = ', '.join([user['login'] for user in top_users])

    # 2. Earliest registered users
    earliest_users = sorted(users, key=lambda x: x['created_at'])[:5]
    earliest_users_logins = ', '.join([user['login'] for user in earliest_users])

    # 3. Most popular licenses
    license_counts = pd.Series([repo['license_name'] for repo in repos if repo['license_name']]).value_counts().head(3)
    popular_licenses = ', '.join(license_counts.index)

    # 4. Majority company
    companies = pd.Series([user['company'] for user in users if user['company']]).value_counts()
    majority_company = companies.idxmax() if not companies.empty else "N/A"

    # 5. Most popular programming language
    languages = pd.Series([repo['language'] for repo in repos if repo['language']]).value_counts()
    popular_language = languages.idxmax() if not languages.empty else "N/A"

    # 6. Second most popular language for users who joined after 2020
    recent_users = [user for user in users if user.get('created_at') and datetime.strptime(user['created_at'], "%Y-%m-%dT%H:%M:%SZ").year > 2020]
    recent_repos = [repo for repo in repos if repo['login'] in [user['login'] for user in recent_users]]
    recent_languages = pd.Series([repo['language'] for repo in recent_repos if repo['language']]).value_counts()
    second_popular_language = recent_languages.index[1] if len(recent_languages) > 1 else ""

    # 7. Language with highest average stars
    repos_df = pd.DataFrame(repos)  # Ensure repos_df is created from repos
    avg_stars = repos_df.groupby('language')['stargazers_count'].mean().idxmax() if not repos_df.empty else "N/A"

    #
