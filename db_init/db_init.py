import sqlite3

if __name__ == '__main__':

    conn = sqlite3.connect('ft8.db')

    cursor = conn.cursor()

    cursor.execute("CREATE TABLE callsigns(callsign, entity_type,license_id, "
                   "name, address, city, state, zip, sgin, frn)")
    #
    # print(cursor.fetchall())
    # cursor.execute("DROP TABLE callsigns")

  # Populate callsigns table:
    with open('l_amat/EN.dat', 'r') as am:
        lines = am.readlines()
        formatted_lines = [line.split("|") for line in lines]
        for line in formatted_lines:
            callsign = str(line[4])
            entity_type = str(line[5])
            license_id = str(line[6])
            name = str(line[7])
            address = str(line[15])
            city = str(line[16])
            state = str(line[17])
            zip = str(line[18])
            sgin = str(line[21])
            frn = str(line[22])
            cursor.execute("""
                           INSERT INTO callsigns (callsign, entity_type, license_id, name, address, city, state, zip,
                                                  sgin, frn)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (callsign, entity_type, license_id, name, address, city, state, zip, sgin, frn))
    conn.commit()
    conn.close()



