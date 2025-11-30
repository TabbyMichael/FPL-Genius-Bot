#!/usr/bin/env python3
"""
Script to help find your FPL team ID
Instructions:
1. Log into the FPL website manually with your Google account
2. Go to https://fantasy.premierleague.com/api/me/
3. Copy the numeric value from the URL in your browser address bar
   Example: https://fantasy.premierleague.com/entry/1234567/ (1234567 is your team ID)
"""

print("FPL Team ID Finder")
print("==================")
print()
print("To find your FPL Team ID:")
print("1. Go to the FPL website: https://fantasy.premierleague.com")
print("2. Log in with your Google account")
print("3. Once logged in, look at the URL in your browser address bar")
print("4. It should look like: https://fantasy.premierleague.com/entry/1234567/")
print("5. The number (1234567 in this example) is your team ID")
print()
print("Please enter your team ID below:")
team_id = input("Team ID: ")

if team_id.isdigit():
    print(f"✓ Valid team ID format: {team_id}")
    print("Update your .env file with this team ID:")
    print(f"TEAM_ID={team_id}")
else:
    print("⚠️  Team ID should be a numeric value. Please check the URL again.")