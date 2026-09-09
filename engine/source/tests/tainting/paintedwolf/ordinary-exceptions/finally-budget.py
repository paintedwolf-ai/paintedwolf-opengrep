def tainted_return():
    value = source_value
    try:
        return value
    finally:
        try:
            value = "safe"
        finally:
            try:
                value = "safe"
            finally:
                try:
                    value = "safe"
                finally:
                    try:
                        value = "safe"
                    finally:
                        try:
                            value = "safe"
                        finally:
                            try:
                                value = "safe"
                            finally:
                                try:
                                    value = "safe"
                                finally:
                                    try:
                                        value = "safe"
                                    finally:
                                        try:
                                            value = "safe"
                                        finally:
                                            try:
                                                value = "safe"
                                            finally:
                                                try:
                                                    value = "safe"
                                                finally:
                                                    try:
                                                        value = "safe"
                                                    finally:
                                                        try:
                                                            value = "safe"
                                                        finally:
                                                            try:
                                                                value = "safe"
                                                            finally:
                                                                value = "safe"


def safe_return():
    value = "safe"
    try:
        return value
    finally:
        try:
            value = "safe"
        finally:
            try:
                value = "safe"
            finally:
                try:
                    value = "safe"
                finally:
                    try:
                        value = "safe"
                    finally:
                        try:
                            value = "safe"
                        finally:
                            try:
                                value = "safe"
                            finally:
                                try:
                                    value = "safe"
                                finally:
                                    try:
                                        value = "safe"
                                    finally:
                                        try:
                                            value = "safe"
                                        finally:
                                            try:
                                                value = "safe"
                                            finally:
                                                try:
                                                    value = "safe"
                                                finally:
                                                    try:
                                                        value = "safe"
                                                    finally:
                                                        try:
                                                            value = "safe"
                                                        finally:
                                                            try:
                                                                value = "safe"
                                                            finally:
                                                                value = "safe"


# ruleid: flow
sink(tainted_return())
# ok: flow
sink(safe_return())
