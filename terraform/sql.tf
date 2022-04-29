resource "google_sql_database_instance" "mysql01" {
  name             = "mysql01"
  database_version = "MYSQL_8_0"
  region           = "us-east4"

  settings {
    tier = "db-f1-micro"
  }
}

resource "google_sql_database" "wordpress" {
  name     = "wordpress"
  instance = google_sql_database_instance.mysql01.name
}

resource "google_sql_user" "wordpress" {
  name     = "wordpress"
  instance = google_sql_database_instance.mysql01.name
  host     = "%"
  password = "wordpress"
}
