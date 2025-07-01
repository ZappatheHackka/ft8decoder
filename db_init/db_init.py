import sqlite3

if __name__ == '__main__':

    conn = sqlite3.connect('ft8.db')

    cursor = conn.cursor()

    # cursor.execute("CREATE TABLE callsigns(callsign, entity_type,license_id, "
    #                "name, address, city, state, zip, sgin, frn)")
    #
    # print(cursor.fetchall())
    # cursor.execute("DROP TABLE callsigns")

  # Populate callsigns table with EN.dat:
  #   with open('l_amat/EN.dat', 'r') as am:
  #       lines = am.readlines()
  #       formatted_lines = [line.split("|") for line in lines]
  #       for line in formatted_lines:
  #           callsign = str(line[4])
  #           entity_type = str(line[5])
  #           license_id = str(line[6])
  #           name = str(line[7])
  #           address = str(line[15])
  #           city = str(line[16])
  #           state = str(line[17])
  #           zip = str(line[18])
  #           sgin = str(line[21])
  #           frn = str(line[22])
  #           cursor.execute("""
  #                          INSERT INTO callsigns (callsign, entity_type, license_id, name, address, city, state, zip,
  #                                                 sgin, frn)
  #                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  #                          """, (callsign, entity_type, license_id, name, address, city, state, zip, sgin, frn))

  # Populating with AM.dat:
  #   cursor.execute("CREATE TABLE am_data(callsign, sys_id, op_class, group_code, region_code, trustee_sign)")

    # with open('l_amat/AM.dat', 'r') as am:
    #     lines = am.readlines()
    #     formatted_lines = [line.split('|') for line in lines]
    #     for line in formatted_lines:
    #         sys_id = line[1]
    #         callsign = line[4]
    #         op_class = line[5]
    #         group_code = line[6]
    #         region_code = line[7]
    #         trustee_sign = line[8]
    #         cursor.execute("""
    #         INSERT INTO am_data (callsign, sys_id, op_class, group_code, region_code, trustee_sign)
    #         VALUES (?, ?, ?, ?, ?, ?)""",
    #                        (callsign, sys_id, op_class, group_code, region_code, trustee_sign))
    # conn.commit()
    # conn.close()

# Joining the two tables into a master table!

    # create_table_query = '''
    # CREATE TABLE master_table AS
    # SELECT callsigns.*, am_data.*
    # FROM callsigns INNER JOIN am_data
    # ON callsigns.callsign = am_data.callsign;
    # '''
    #
    # cursor.execute(create_table_query)
    # conn.commit()
    # conn.close()




