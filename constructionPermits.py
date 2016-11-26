'''
11/12/2016

This script scrapes construction permit information from NYCDOT's NYC Active Street Construction 
Permits webpage (see url below). This permit information is then saved to csv file in the current
directory (see fileName below).
'''

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import Select
import mechanize
import numpy as np
import sys
import csv

reload(sys)
sys.setdefaultencoding('utf-8')

url = "http://a841-dotweb01.nyc.gov/permit/permit/web_permits/permitsearchform.asp"
fileName = 'constructionPermits_test.csv'


'''
MAIN FUNCTIONS
'''
def getOnStreetOptions():
    '''
    Selects 'Manhattan' for the selection on the Borough drop down menu. This updates the 
    available selection options for the "On Street" drop down menu. 

    This function then saves all of these available On Street selections as a list and 
    returns this list.
    '''
    
    streets = []    
    
    # Use the mechanize library to first selection Manhattan, which updates the available
    # selection options for the "On Street" drop down menu.
    browser = mechanize.Browser()    
    browser.set_handle_robots(False)     # ignore robots
    browser.set_handle_refresh(False)    
    browser.open(url)
    browser.select_form(name="PermitSearch")
    browser.form["borough"] = ["1"]           # 1 corresponds to Manhattan
    browser.submit()
    
    # Collect the "On Street" drop down menu options as a BeautifulSoup object.
    soup = BeautifulSoup(browser.response().read(), "lxml")
    # Lines 21-699 of the entries tagged as <option> correspond to all possible "On Street" options for Manhattan.
    onStreetValues = soup.find_all('option')[21:699] 

    # Build the streets list
    for street in onStreetValues:
        streets.append(street.text.strip())
        
    return streets


def scrapeAndSaveData(streets, numStreets=0):  
    '''
    Scrapes all of the permit information available for the borough of Manhattan by each "On Street" street
    option. 
    Saves this permit information to csv file in current directory.
    Returns failedStreets and numStreets.

    Inputs:
    streets: A list of all of the "On Street" street options that should be processed.
    numStreets: Counter to track the number of streets processed. Default setting is 0, which means a header
    row will be added to the csv file.

    Outputs:
    failedStreets: Returns a list of the streets that the website failed to load properly.
    numStreets: Returns an integer numStreets, which counts the number of streets processed (successfully and 
    unsuccessfully) by this function.    
    '''
    
    print "Scraping data for %s streets..." %(len(streets))   
    
    numBlankStreets = 0 # Counter to keep track of the number of streets that don't have permit entries.
    blankStreets = []

    numFailedStreets = 0 # Counter to keep track of the number of streets the website fails to load properly.
    failedStreets = []

    for street in streets: 
        numStreets += 1  

        try:
            # Use beautiful soup to handle the html code.
            soup = getSoup(street)   
            
            # Check if table has entries ('click column name to sort') or is blank ('No permits found').         
            tableStatus = soup.findAll('b')[0].text.strip()             
            
            # If table is not blank (has permit info for this street).          
            if (tableStatus == 'click column name to sort'): 
                permitsDf, headers = createPermitsDf(soup)
                # Add headers to the csv file only once (the very first time)
                if (numStreets == 1):
                    addHeaders(headers)                
                 
                saveToCSV(permitsDf)  
                print "%s: Permit information for %s is saved to file." %(numStreets, street)
            # Else table is blank (no permit info for this street).
            else: 
                numBlankStreets += 1
                blankStreets.append(street)
                print "%s: %s is blank." %(numStreets, street)   

        # Accounts for when the website sometimes fails to load properly.
        except:
            numFailedStreets += 1
            failedStreets.append(street)
            print "%s: %s failed to load properly from the website." %(numStreets, street) 
    
    # Print scraping summary after iterating through all streets.
    print "\nSCRAPING SUMMARY:"
    print "%s streets processed." %(numStreets)

    print "%s of these streets were blank (did not have permit information)." %(numBlankStreets)
    if (numBlankStreets > 0): print "The blank street(s) are: %s." %(blankStreets)

    print "%s of these streets failed to load properly." %(numFailedStreets)
    if (numFailedStreets > 0): print "The failed street(s) are: %s." %(failedStreets)
    
    print "\nPermit information for %s streets saved to %s." %(numStreets-numBlankStreets-numFailedStreets, fileName)

    return failedStreets, numStreets


def secondAttempt(failedStreets, numStreetsProcessed): 
    '''
    Runs the scrapeAndSaveData function again, with the subset of streets that failed to load properly the
    first time. Prints summary.

    Inputs:
    failedStreets: A list of the streets that failed to load properly the first time.
    numStreetsProcessed: An integer of the number of streets that were processed (successfully and unsuccessfully)
    the first time. This is basically used to ensure that a header row doesn't get added to the csv file again.
    '''

    def printSuccess():
        print "\nFinished scraping construction permit information from %s!" %(url)
        print "\nAll streets saved to %s successfully!" %(fileName)

    if (len(failedStreets) > 0):
        print "\nTrying the failed streets again to see if they load properly this time."
        failedStreets, numStreetsProcessed = scrapeAndSaveData(failedStreets, numStreets=numStreetsProcessed)     
    
        if (len(failedStreets) > 0):
            print "One or more streets failed to load during the second try. Please manually check the failed streets."
        else:
            printSuccess()
    else:
        printSuccess()


'''
HELPER FUNCTIONS FOR scrapeAndSaveData function
'''
def getSoup(street):
    '''
    Takes an OnStreet street option and obtains the html pop up table with permit information
    from the website for this street option. Converts this permit information table to a 
    BeautifulSoup object for further processing.

    Input: One OnStreet street option as a string.
    Output: Permit information table as a BeautifulSoup object.
    '''
    ## Use the selenium library to simulate being a human user.
    # Create a Chrome browser driver.
    driver = webdriver.Chrome()
    driver.get(url)    
    
    # Select desired borough on the dropdown menu.
    select = Select(driver.find_element_by_name('borough'))
    select.select_by_value('1') # 1 corresponds to Manhattan  

    # Select the street from the OnStreet drop down menu.
    select = Select(driver.find_element_by_name('on_street'))
    select.select_by_value(street)
   
    # Click the "SEARCH PERMITS" button, which will result in a new pop up window with a table of 
    # construction permits information for the street.
    driver.find_element_by_css_selector("input[type='button'][value='SEARCH PERMITS']").click()
    # Switch over to the pop up window with the table of construction permits.
    driver.switch_to_window(driver.window_handles[-1])

    # Convert permit information to a BeautifulSoup object.
    soup = BeautifulSoup(driver.page_source, "lxml")

    driver.quit()     

    return soup


def createPermitsDf(soup):
    '''
    Converts a BeautifulSoup version of the permit information to a pandas dataframe.

    Input:
    soup: A BeautifulSoup object containing the permit information for one OnStreet street.

    Outputs:
    df: The dataframe version of the permit information for one OnStreet street.
    headers: A list of the headers corresponding to the permit information table. The headers match the 
    header names used on the website, minus whitespace.
    '''
    headers = createHeaders(soup)
    permits = createPermits(soup, len(headers))
    
    # Create a dictionary first and then a pandas dataframe.
    dictionary = dict(zip(headers, permits))

    df = pd.DataFrame(dictionary)
    df = df[headers] # Reorder the columns to match the order of the headers.

    # Perform basic cleaning of the df.
    df = df.apply(lambda x: x.str.strip()).replace('', np.nan) # replace blanks with NaN
    df.dropna(how='all', inplace=True) # drop rows that contain all blank elements
    df.drop_duplicates() # drop duplicate rows
 
    return df, headers


def addHeaders(headers):
    '''
    Adds the headers for the permit information table that's saved to csv. Should only be called once
    (when the very first street is processed).

    Input:
    headers: A list of the headers corresponding to the permit information tables. The headers match the 
    header names used on the website, minus whitespace.
    '''    
    with open(fileName, 'a') as f:
        writer = csv.writer(f)
        writer.writerow(headers)


def saveToCSV(df): 
    '''
    Appends permit information to csv without indices and headers.

    Input:
    df: The dataframe version of the permit information for one OnStreet street.
    '''
    with open(fileName, 'a') as f:
        df.to_csv(f, index=False, header=False)


def createHeaders(soup):
    '''
    Input:
    soup: A BeautifulSoup object containing the permit information for one OnStreet street.

    Output:
    headers: A list of the headers corresponding to the permit information table. The headers match the 
    header names used on the website, minus whitespace.
    '''
    headers = []
    soupHeaders = soup.findAll('th')

    for h in soupHeaders:
        headers.append(h.text.replace(" ", ""))  #get rid of whitespace for table headers
    
    return headers       


def createPermits(soup, numHeaders):   
    '''
    Input:
    soup: A BeautifulSoup object containing the permit information for one OnStreet street.
    numHeaders: The number of headers that the permit information table has.

    Output:
    permits: A list of lists, where each nested list corresponds to the elements in a particular
    column of permit information. The index of this list corresponds to the order of the headers list.
    '''    
    permits = [[] for i in range(numHeaders)]

    rows = soup.findAll('tr')
    for row in rows[3:]: # Iterate through all of the rows in the permit table.
        col = row.findAll('td')

        # Save each element to its respective column (ie, nested list).
        for i in range(numHeaders):
            try:
                permits[i].append(col[i].text.strip())
            # IndexError thrown when table entry is blank; make these entries blank with ''.
            except IndexError: 
                permits[i].append('')

    return permits

   

def main():
    '''
    WEBSITE DESCRIPTION
    The NYC DOT website instructs that 2 of the 8 different drop down menus need to be selected in order
    to obtain active construction permit information. Furthermore, the selection for a drop down menu 
    influences the selections available for the other drop down menus. 

    After making selections from 2 drop down menus, clicking "SEARCH PERMITS" results in a pop up window with
    permit information in the form of a table.

    SCRIPT OVERVIEW 
    (1) Select Manhattan for the "Borough" drop down menu option.
    (2) Obtain all of the possible selections for the "On Street" drop down menu that appear after selecting 
    Manhattan (used the mechanize library for this).
    (3) Iterate through all possible "On Street" streets in Manhattan and scrape the permit data for these
    streets (used the selenium library for this).
    (4) Perform some basic data cleaning operations and save scraped data to csv file.
    (5) Since the website sometimes fails to load a street properly, retry the failed streets again by going 
    through steps (3) and (4) again with just the failed streets.
    (6) Manually inspect any streets that failed to load properly after the second attempt.
    '''
    
    # Steps (1) and (2) of SCRIPT OVERVIEW
    onStreetOptions = getOnStreetOptions()

    # Steps (3) and (4) of SCRIPT OVERVIEW
    failedStreets, numStreetsProcessed = scrapeAndSaveData(onStreetOptions)
    
    # Step (5) of SCRIPT OVERVIEW
    secondAttempt(failedStreets, numStreetsProcessed)
   

main()