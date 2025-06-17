import math
import maidenhead as mh
import adif_io
from haversine import haversine, Unit

#path to your log file
ADIF_FILE = './wsjtx_log.adi'

def maidenhead_to_latlon(grid):
    #need to use the center of the grid for scoring
    lat, lon = mh.to_location(grid, center=True)
    return (lat, lon)

def score_qso(grid1, grid2):
    point1 = maidenhead_to_latlon(grid1)
    point2 = maidenhead_to_latlon(grid2)

    #find great circle distance, points are based on short path
    distance = haversine(point1, point2, unit=Unit.KILOMETERS)

    #scoring
    #1 base point per qso
    #1 point for each 500km between grids
    #points are rounded up to the next integer 
    #example: two grids 1565km apart get 1 base point and 3.13 for distance
    #rounded up it's 1 + 4 for 5 total points
    points = 1 + math.ceil(distance / 500)

    return points, distance

def main():
    try:
        qsos, _ = adif_io.read_from_file(ADIF_FILE)
    except Exception as e:
        print(f"Error reading ADIF file: {e}")
        exit(1)

    #running score
    score = 0

    #these stats aren't needed for the conest, but are interesting
    shortest_qso = {'call': 'NONE', 'band': 'NONE', 'distance': 999999999, 'points': 0}
    longest_qso = {'call': 'NONE', 'band': 'NONE', 'distance': 0, 'points': 0}
    total_dist = 0

    #keep track of qsos and points per band, also not needed for the contest
    #band_summary['20m'] = {'contacts': 0, 'points': 0}
    band_summary = {}

    #keep track of unique qsos 
    #a station can be worked once per band, regardless of mode
    unique_qsos = set()

    #loop through all the qsos in the log
    for qso in qsos:
        #get the callsign and band
        who = qso.get('CALL', 'ERROR')
        band = qso.get('BAND', 'ERROR')

        #validate that we have grid squares for ourselves and the other station
        grid1 = qso.get('MY_GRIDSQUARE', 'ZZ00')
        grid2 = qso.get('GRIDSQUARE', 'ZZ00')
        if grid2[:4] == 'ZZ00':
            print(f"Missing GRIDSQARE for {who} on {band}, skipping QSO!")
            continue

        #initialize the band summary pair if this is the first qso on this band
        if band not in band_summary:
            band_summary[band] = {'contacts': 0, 'points': 0}

        #make sure it's a unique qso
        #you can only receive credit for working a station once per band, regardless of mode
        qso_pair = (who, band)
        if qso_pair in unique_qsos:
            print(f"{who}: DUPE on {band}")
            continue

        #get the qso score
        points, dist = score_qso(grid1, grid2)

        #add to running total
        score += points

        #distance info
        total_dist += dist
        if dist > longest_qso['distance']:
            longest_qso = {'call': who, 'band': band, 'distance': dist, 'points': points}
        if dist < shortest_qso['distance']:
            shortest_qso = {'call': who, 'band': band, 'distance': dist, 'points': points}

        #keep track of number of qsos and total points for each band
        band_summary[band]['contacts'] += 1
        band_summary[band]['points'] += points
        
        #add qso so we can detect future dupes
        unique_qsos.add(qso_pair)

        #display QSO info
        print(f"{who}: {band}, {grid2}, {dist:.0f} km, {points} points")
    
    #calculate average points per qso
    unique = len(unique_qsos)
    average = score / unique

    #display the report
    print()
    print(f"Unique QSOs: {unique}")
    print(f"Dupe QSOs: {len(qsos) - unique}")
    print(f"Total Score: {score}")
    print(f"Average Score per QSO: {average:.2f}")
    print()
    print(f"Shortest QSO: {shortest_qso['call']}, {shortest_qso['band']}, {shortest_qso['distance']:.0f} km, {shortest_qso['points']} points")
    print(f"Longest QSO: {longest_qso['call']}, {longest_qso['band']}, {longest_qso['distance']:.0f} km, {longest_qso['points']} points")
    print(f"Total distance of all QSOs: {total_dist:.0f} km")
    print()
    print("Band Breakdown")

    #print out band breakdown
    for band, data in sorted(band_summary.items()):
        unique = data['contacts']
        points = data['points']
        average = points / unique
        print(f"Band {band}: {unique} contact(s), {points} total points, {average:.2f} points average")

if __name__ == "__main__":
    main()
