from blogengine import app

# * the program starts here
if __name__ == '__main__':
    # ! take out the debug argument
    app.run(port=8000, debug=True)