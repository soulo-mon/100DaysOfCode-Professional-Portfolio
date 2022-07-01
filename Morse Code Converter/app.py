MC = "morse_code"


def load_char():
    # load content of the txt file
    with open(MC, mode="r", encoding="utf-8") as f:
        # using dictionary comprehension
        mc_dict = {line.split(" ")[0]: line.split(" ")[1].strip("\n") for line in f.readlines()}
    return mc_dict


def get_input():
    """Takes an input from the user and returns it as a STR."""
    while True:
        print("Please enter the text to convert:")
        input_text = input("> ").lower()

        # make sure something was entered
        if input_text == "":
            print("Please enter some text.")
        else:
            return input_text


def main():
    # load the chart into a dict
    morse_chart = load_char()
    print("Welcome to the Morse code converter.\n")

    while True:
        # get input from the user
        input_text = get_input()
        converted_text = ""

        # process characters
        for char in input_text:
            # only add valid convertible characters, ignore everything else
            if char in morse_chart:
                # add a space after each character
                converted_text += morse_chart[char] + " "

        # check for empty output
        if len(converted_text) > 0:
            print(f"Your input in morse code: {converted_text}")
        else:
            print("The input did not contain any convertible character.")

        # condition to break out of the loop
        print("Do you want to convert something else? (y/n)")
        if input("> ").lower() == "n":
            break

    print("Goodbye.")


if __name__ == "__main__":
    main()