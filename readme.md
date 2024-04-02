# Bangsaen Map

## Git Repository

https://github.com/Poonnachit/neo4j_project.git

## Description

This project is about creating a map of Bangsean city. The map consists of nodes and relations.
The nodes are the places in Bangsean city and the relations are the roads that connect the nodes.
The program allows users to add, edit, delete nodes and relations. Users can also find the shortest path
between two nodes by distance and by node. The program is implemented using python3 and neo4j.

## Notes

This program can handle more than 2 intersects when delete node by create new relation between related nodes

How I handle more than 2 intersects when delete node:

if related node already have relation with other related node

- this program will not create new relation because it already has relation

else

- create new relation between related nodes by calculate total distance between 2 related nodes

## Problems

when create new relation between related nodes, the program don't know the name of the road,s
it will automatically set the name of the road to the name of the start node to the end node,
but you can enter the name of the road manually

## Requirements

- python 3.11
- Neo4j 5.18.1
- Graph Data Science 2.6.2

## Prerequisites

1. Create a virtual environment `python -m venv venv`
2. Activate the virtual environment `venv\Scripts\activate.ps1` or `venv\Scripts\activate.bat`
3. Install the requirements  `pip install -r requirements.txt`

## Usage

- Run main.py `python main.py`
- Follow the instructions

## Folder Structure

### 64160038<br>

├── bangsean_data.txt <br>
├── main.py <br>
├── requirements.txt <br>
├── readme.md <br>
├── .gitignore <br>

| Folder Structure  | Description                                                                      |
|-------------------|----------------------------------------------------------------------------------|
| bangsean_data.txt | a text file that contain cypher to create node and relationship of bangsean data |
| main.py           | main file for user to interact with db                                           |
| requirements.txt  | list of requirements                                                             |
| readme.md         | this file                                                                        |
| .gitignore        | file to ignore files and folders                                                 |

## Created By

Poonnachit Amnuaypornpaisal<br>
Burapha University<br>
Student ID: 64160038