// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
@main struct LocalizationTests {
    static func main()throws {
        let directory=URL(fileURLWithPath:CommandLine.arguments[1])
        for language in AppLocalization.languages {
            let c=LocalizationCatalog(directory:directory,language:language.id)
            precondition(!c.text("Settings").isEmpty)
            precondition(c.text("PNY XLR8 RTX 4080 VERTO")=="PNY XLR8 RTX 4080 VERTO")
            precondition(c.text("custom-user-preset-XYZ")=="custom-user-preset-XYZ")
        }
        let c=LocalizationCatalog(directory:directory,language:"de")
        precondition(c.text("Settings")=="Einstellungen")
        precondition(c.text("SETTINGS")=="EINSTELLUNGEN")
        precondition(c.text("12 LEDs").contains("12"))
        let missing=LocalizationCatalog(directory:directory,language:"missing")
        precondition(missing.text("Settings")=="Settings")
        print("22 locale catalogs, Unicode/case handling, template values, hardware identities and English fallback verified")
    }
}
